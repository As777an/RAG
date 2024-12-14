import json
import os
from groq import Groq
from langchain_community.callbacks import get_openai_callback
from langgraph.graph import END, StateGraph
from langchain import hub
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel as bm
from langchain_core.output_parsers import StrOutputParser
from langchain_openai import ChatOpenAI
from pprint import pprint
from langchain_community.tools.tavily_search import TavilySearchResults
from langchain.schema import Document
from .loader_chroma import *
from .classes import *


# Устанавливаем переменные окружения
os.environ['OPENAI_API_KEY'] = '???'
os.environ['LANGCHAIN_TRACING_V2'] = 'true'
os.environ['LANGCHAIN_ENDPOINT'] = 'https://api.smith.langchain.com'
os.environ['LANGCHAIN_API_KEY'] = '???'
os.environ['GROQ_API_KEY'] = '???'
os.environ['TAVILY_API_KEY'] = '???'

# Используем DirectoryLoader для загрузки документов из папки
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_ROOT = os.path.join(BASE_DIR, 'blog/data/MD')
DATA_ROOT_EN = os.path.join(BASE_DIR, 'blog/data_en/MD')
DATA_ROOT_KZ = os.path.join(BASE_DIR, 'blog/data_kz/MD')
CHROMA_ROOT = os.path.join(DATA_ROOT, 'vectorstore')
CHROMA_ROOT_EN = os.path.join(DATA_ROOT_EN, 'vectorstore')
CHROMA_ROOT_KZ = os.path.join(DATA_ROOT_KZ, 'vectorstore')
language = 'en'
print(f'BASE ROOT: {BASE_DIR}')
print(f'DATA ROOT: {DATA_ROOT}')
print(f'CHROMA ROOT: {CHROMA_ROOT}')

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


token_usage = {"openai": 0, "llama": ''}

token_cost_process = TokenCostProcess()

# LLM with function call
llm = ChatOpenAI(model="gpt-3.5-turbo-0125", temperature=0, callbacks=[CostCalcAsyncHandler( "gpt-3.5-turbo-0125", token_cost_process ) ],)
structured_llm_grader = llm.with_structured_output(GradeDocuments)

# Prompt
system = """Please analyze the provided text by following these steps:\n
First, classify the text to determine whether it contains extremist content.\n
If signs of extremism are detected, evaluate the probability that the text contains extremist content on a scale from 0 to 1, where 0 represents a complete absence of extremist indicators and 1 indicates absolute certainty of extremist elements.\n
If extremist content is identified, further classify it according to the specific type of extremism it represents. The types of extremism to consider are as follows: Political extremism involves expressions that diminish patriotism, undermine civic stances, or aim to insult authorities; Religious extremism encompasses expressions with ambiguous or negative religious contexts; National or ethnic extremism refers to the use of violence to infringe on rights based on ethnicity or to incite hatred; Racial extremism involves the use of violence based on race or actions inciting racial hatred; Economic extremism pertains to the use of violence to achieve economic goals; Social extremism relates to the use of violence to alter the social order or address inequality; Youth extremism includes violence perpetrated by youth, often driven by xenophobia or vandalism; Lastly, environmental extremism refers to the use of violence to protect the environment, such as during protests against deforestation."""
grade_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", system),
        ("human", "Retrieved document: \n\n {document} \n\n User question: {question}"),
    ]
)

retrieval_grader = grade_prompt | structured_llm_grader

class JsonSchema(bm):
    source: str

def detect_type_of_question(state):
    """
    Detect if person wants to get answer from web or from documents

    Args:
        state (dict): The current graph state

    Returns:
        web - if user wants answer from web
        doc - if person wants answer from documents
    """
    print("---DETECTING SOURCE---")
    question = state["question"]
    try:
        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": f'Detect from the question which source the user wants to get the answer from. If the user asks to find the question on the internet, it must be "web". If there are keywords like web, it must be "web". If there is no direct indication to search on the internet, it must be "doc". For example: question: what is instagram?, answer: doc; question: find on the internet, what is instagram, answer: web.   The JSON object must use the schema: {{"source": source}}. Question: {question}',
                }
            ],
        model="llama3-8b-8192",
        # Enable JSON mode by setting the response format
        response_format={"type": "json_object"},
        )
        result = chat_completion.choices[0].message.content
        token_usage['llama'] = chat_completion.usage
        result = json.loads(result)
        return result['source']
    except Exception as e:
        return 'error'

def retrieve(state):
    """
    Retrieve documents

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, documents, that contains retrieved documents
    """
    print(f'LANGUAGE: {language}')
    if language == 'kk':
        chroma = load_chroma(CHROMA_ROOT_KZ)
    elif language == 'en':
        chroma = load_chroma(CHROMA_ROOT_EN)
    else:
        chroma = load_chroma(CHROMA_ROOT)
    retriever = chroma.as_retriever()
    print("---RETRIEVE---")
    question = state["question"]
    print(question)
    print()
    print(state["documents"])
    # Retrieval

    try:
        documents = retriever.get_relevant_documents(question)
        print(f'DOCUMENTS: {documents}')
        return {"documents": documents, "question": question}
    except Exception as e:
        return {"documents": [], "question": question, "error": e}


def generate(state):
    """
    Generate answer

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, generation, that contains LLM generation
    """
    print("---GENERATE---")
    question = state["question"]
    documents = state["documents"]

    prompt = hub.pull("rlm/rag-prompt")

    rag_chain = prompt | llm | StrOutputParser()
    # RAG generation
    
    try:
        generation = rag_chain.stream({"context": documents, "question": question})
        print( token_cost_process.get_cost_summary( "gpt-3.5-turbo" ) )
        return {"documents": documents, "question": question, "generation": generation}
    except Exception as e:
        print(f'Error while generating: {e}')


def grade_documents(state):
    """
    Determines whether the retrieved documents are relevant to the question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with only filtered relevant documents
    """

    print("---CHECK DOCUMENT RELEVANCE TO QUESTION---")
    question = state["question"]
    documents = state["documents"]


    # Score each doc
    filtered_docs = []
    for d in documents:
        score = retrieval_grader.invoke(
            {"question": question, "document": d.page_content}
        )
        grade = score.binary_score
        if grade == "yes":
            print("---GRADE: DOCUMENT RELEVANT---")
            filtered_docs.append(d)
        else:
            print("---GRADE: DOCUMENT NOT RELEVANT---")
            continue
    return {"documents": filtered_docs, "question": question}


def transform_query(state):
    """
    Transform the query to produce a better question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates question key with a re-phrased question
    """

    print("---TRANSFORM QUERY---")
    question = state["question"]
    documents = state["documents"]

    # Prompt
    system = """You a question re-writer that converts an input question to a better version that is optimized \n 
        for vectorstore retrieval. Look at the input and try to reason about the underlying sematic intent / meaning."""
    re_write_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", system),
            (
                "human",
                "Here is the initial question: \n\n {question} \n Formulate an improved question.",
            ),
        ]
    )

    question_rewriter = re_write_prompt | llm | StrOutputParser()

    try:
        better_question = question_rewriter.invoke({"question": question})
        return {"documents": documents, "question": better_question}
    except Exception as e:
        return {"documents": documents, "question": question, "error": e}

def catch_error(state):
    """From dictionary recognize, if there were erros in the current state"""
    if "error" in state:
        print(state['error'])
        return "error"
    else:
        return "next"


def decide_to_generate(state):
    """
    Determines whether to generate an answer, or re-generate a question.

    Args:
        state (dict): The current graph state

    Returns:
        str: Binary decision for next node to call
    """

    print("---ASSESS GRADED DOCUMENTS---")
    filtered_documents = state["documents"]

    if not filtered_documents:
        # All documents have been filtered check_relevance
        # We will re-generate a new query
        print(
            "---DECISION: ALL DOCUMENTS ARE NOT RELEVANT TO QUESTION, TRANSFORM QUERY---"
        )
        return "transform_query"
    else:
        # We have relevant documents, so generate answer
        print("---DECISION: GENERATE---")
        return "generate"

def ask_question(state):
    """
    Ask a question directly to the language model.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): New key added to state, model_question, that contains LLM generated question
    """
    print("---ASK QUESTION---")

    # Получаем вопрос из состояния
    question = state["question"]
    # filtered_documents = state["documents"]
    question = question + f'\n Answer in users language'
    
    response = llm.stream(question)
    
    return {"question": question, "generation": response}

def web_search(state):
    """
    Web search based on the re-phrased question.

    Args:
        state (dict): The current graph state

    Returns:
        state (dict): Updates documents key with appended web results
    """

    print("---WEB SEARCH---")
    question = state["question"]
    documents = state["documents"]

    # Web search
    web_search_tool = TavilySearchResults(k=2)
    try:
        docs = web_search_tool.invoke({"query": question})
        web_results = "\n".join([d["content"] for d in docs])
        web_results = Document(page_content=web_results)
        documents.append(web_results)

        return {"documents": documents, "question": question}
    except Exception as e:
        return {"documents": [], "question": question, "error": e}




workflow = StateGraph(GraphState)
# Define the nodes
workflow.add_node("first_retrieve", retrieve)  # Этот узел отвечает за первичное извлечение данных или документов
workflow.add_node("second_retrieve", retrieve)  # Этот узел также отвечает за извлечение данных или документов
workflow.add_node("first_grade_documents", grade_documents)  # Этот узел отвечает за первичную оценку документов
workflow.add_node("web_search", web_search)  # Этот узел отвечает за поиск веб-ресурсов
workflow.add_node("second_grade_documents", grade_documents)  # Этот узел также отвечает за оценку документов, но после вторичного извлечения
workflow.add_node("generate", generate)  # Этот узел отвечает за генерацию чего-либо
workflow.add_node("transform_query", transform_query)  # Этот узел отвечает за трансформацию запроса или данных
workflow.add_node("ask_question", ask_question)  # Этот узел отвечает за задание вопроса модели

# Build graph
'''
Устанавливает узел first_retrieve в качестве начальной точки входа в граф. 
Это означает, что процесс обработки запроса начинается с этого узла.
'''
workflow.set_entry_point("first_retrieve")

'''
Добавляет условные переходы из узла source на основе результата функции condition_function. 
edges_dict содержит ключи, которые представляют возможные результаты функции, и значения, 
которые указывают на узлы, к которым происходит переход в случае соответствующего результата.
Например, для узла first_retrieve добавляются условные переходы в зависимости от типа вопроса (web, doc или error). 
Если тип вопроса равен web, происходит переход к узлу web_search, если doc, то к first_grade_documents, 
а если тип не определен (error), то происходит переход к узлу ask_question.
'''
workflow.add_conditional_edges(
    "first_retrieve",
    detect_type_of_question,
    {
        "web": "web_search",
        "doc": "first_grade_documents",
        "error": "ask_question"
    },
)

'''
Для узлов transform_query, web_search и других добавляются условные переходы для обработки ошибок. 
Если происходит ошибка в выполнении функции, то происходит переход к узлу ask_question.
'''
workflow.add_conditional_edges(
    "transform_query",
    catch_error,
    {
        "next": "second_retrieve",
        "error": "ask_question"
    },
)

workflow.add_conditional_edges(
    "web_search",
    catch_error,
    {
        "next": "generate",
        "error": "ask_question"
    },
)

'''
У узла first_grade_documents есть условные переходы в зависимости от результата функции decide_to_generate. 
Если результат равен transform_query, то происходит переход к узлу transform_query, а если generate, то к узлу generate.
'''
workflow.add_conditional_edges(
    "first_grade_documents",
    decide_to_generate,
    {
        "transform_query": "transform_query",
        "generate": "generate",
    },
)


workflow.add_conditional_edges(
    "second_retrieve",
    detect_type_of_question,
    {
        "web": "web_search",
        "doc": "second_grade_documents",
        "error": "ask_question"
    },
)


workflow.add_conditional_edges(
    "second_grade_documents",
    decide_to_generate,
    {
        "transform_query": "ask_question",
        "generate": "generate"
    },
)

'''
Устанавливает завершающий узел END после узла generate. 
Это означает, что после выполнения узла generate процесс завершается.
То же самое для узла ask_question.
'''
workflow.add_edge("generate", END)
workflow.add_edge("ask_question", END)  # Конец после ask_question


# Compile
'''
Компилирует граф в приложение, которое можно запустить для обработки запросов или данных 
в соответствии с определенной логикой переходов и функциями обработки.
'''
app = workflow.compile()


def website_language(lang):
    global language
    language = lang
    return True


# Run
def generate_answer(inputs):
    print(f'INITIAL: {inputs}')
    website_language(inputs.get("language"))
    print(f'SECOND INITIAL: {inputs}')
    ans = ''
    for output in app.stream(inputs):
        for key, value in output.items():
            pprint(f"Node '{key}':")
            if key == "generate":
                for generated_question in value["generation"]:
                    ans += generated_question
            elif key == "ask_question":
                for generated_question in value["generation"]:
                    ans += generated_question.content
            pprint(f'ANSWER: {ans}')
        pprint("\n---\n")
    return str(ans)


# model_name = "gpt-3.5-turbo" 
# summary_text = f"Model: {model_name}\n{token_cost_process.get_cost_summary(model_name)}\n\nGROQ Llama 8b\nTotal tokens used: {token_usage['llama']}"

# with open("summary.txt", "w") as file:
#     file.write(summary_text)
