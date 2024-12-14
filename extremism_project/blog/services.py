from django.conf import settings
from django.utils.translation import gettext_lazy as _
from openai import OpenAI

import snscrape.modules.telegram as telegram
import os


os.environ['OPENAI_API_KEY'] = '???'
client = OpenAI()


def get_telegram_posts(channel: str, limit: int = 2) -> list[str]:
	posts = []
	posts_scraper = telegram.TelegramChannelScraper(channel).get_items() # получает все посты из указанного канала channel
	for post in posts_scraper:
		posts.append(post.content)
		if limit:
			if len(posts) == limit:
				break
	return posts


def get_gpt_analyze(message: str, language: str, engine: str = 'gpt-4o', gpt_model: str = 'ChatGPT') -> str:
	"""
    Get GPT analyze for a given message.

    Parameters:
    - message (str): The input message to analyze.
	- language (str): current user language (kk, ru, en)
	- engine (str): gpt engine

    Returns:
    str: The generated response from GPT.

    Example:
    ```python
    message_to_analyze = "This is the message you want to analyze."
    result = get_gpt_response(message_to_analyze)
    print(result)
    ```
    """

	system_msg = f'You are a helpful assistant who understands extremism'

	error_msg = 'Сервер перегружен'

	if gpt_model != 'ChatGPT':
		prompt = 'Проанализируй вопрос пользователя и дай ответ'
	else:
		prompt = '''Пожалуйста, проанализируйте предоставленный текст, следуя этим шагам: 
			1. Сначала классифицируйте текст, чтобы определить, содержит ли он экстремистское содержание.  
			2. Если признаки экстремизма обнаружены, оцените вероятность того, что текст содержит экстремистское содержание, по шкале от 0 до 1, где 0 означает полное отсутствие признаков экстремизма, а 1 — абсолютную уверенность в наличии экстремистских элементов.  
			3. Если экстремистское содержание выявлено, далее классифицируйте его по конкретному типу экстремизма. Рассматриваются следующие типы экстремизма:  
			   - Политический экстремизм включает выражения, которые унижают патриотизм, подрывают гражданскую позицию или направлены на оскорбление властей.  
			   - Религиозный экстремизм охватывает выражения с двусмысленным или негативным религиозным контекстом.  
			   - Национальный или этнический экстремизм относится к применению насилия для ущемления прав по национальному признаку или разжиганию ненависти.  
			   - Расовый экстремизм включает применение насилия по признаку расы или действия, разжигающие расовую ненависть.  
			   - Экономический экстремизм касается применения насилия для достижения экономических целей.  
			   - Социальный экстремизм связан с применением насилия для изменения социального порядка или устранения неравенства.  
			   - Молодёжный экстремизм включает насилие, совершаемое молодёжью, часто вызванное ксенофобией или вандализмом.  
			   - Экологический экстремизм относится к применению насилия для защиты окружающей среды, например, во время протестов против вырубки лесов.

			Текст:
			'''

	if language == 'en':
		if gpt_model != 'ChatGPT':
			prompt = "Analyze the user's question and provide an answer"
		else:
			prompt = '''Please analyze the provided text by following these steps:
			1. First, classify the text to determine whether it contains extremist content.
			2. If signs of extremism are detected, evaluate the probability that the text contains extremist content on a scale from 0 to 1, where 0 represents a complete absence of extremist indicators and 1 indicates absolute certainty of extremist elements.
			3. If extremist content is identified, further classify it according to the specific type of extremism it represents. The types of extremism to consider are as follows:
			   - Political extremism involves expressions that diminish patriotism, undermine civic stances, or aim to insult authorities.
			   - Religious extremism encompasses expressions with ambiguous or negative religious contexts.
			   - National or ethnic extremism refers to the use of violence to infringe on rights based on ethnicity or to incite hatred.
			   - Racial extremism involves the use of violence based on race or actions inciting racial hatred.
			   - Economic extremism pertains to the use of violence to achieve economic goals.
			   - Social extremism relates to the use of violence to alter the social order or address inequality.
			   - Youth extremism includes violence perpetrated by youth, often driven by xenophobia or vandalism.
			   - Lastly, environmental extremism refers to the use of violence to protect the environment, such as during protests against deforestation.

			Text:
			'''
		error_msg = 'Server is overloaded'
	elif language == 'kk':
		if gpt_model != 'ChatGPT':
			prompt = 'Пайдаланушының сұрағын талдап, жауап беріңіз'
		else:
			prompt = '''Берілген мәтінді келесі қадамдар бойынша талдаңыз:  
			1. Алдымен мәтінді жіктеп, оның экстремистік мазмұнды қамтитынын анықтаңыз.  
			2. Егер экстремизм белгілері анықталса, мәтінде экстремистік мазмұнның бар-жоғын 0-ден 1-ге дейінгі шкала бойынша бағалаңыз, мұндағы 0 экстремизм көрсеткіштерінің толық болмауын, ал 1 экстремистік элементтердің бар екендігіне толық сенімділікті білдіреді.  
			3. Егер экстремистік мазмұн анықталса, оны тиісті экстремизм түріне қарай қосымша жіктеңіз. Қарастырылатын экстремизм түрлері мыналар:  
  			   - Саяси экстремизм** патриотизмді төмендететін, азаматтық ұстанымды әлсірететін немесе билікті қорлауға бағытталған сөз тіркестерін қамтиды.  
  			   - Діни экстремизм** екіұшты немесе теріс діни контекстері бар сөздерді қамтиды.  
 			   - Ұлттық немесе этникалық экстремизм** этникалық ерекшеліктерге негізделген құқықтарды бұзуға немесе жеккөрушілікті қоздыруға бағытталған зорлық-зомбылықты білдіреді.  
 			   - Нәсілдік экстремизм** нәсілге негізделген зорлық-зомбылықты немесе нәсілдік жеккөрушілікті қоздыратын әрекеттерді қамтиды.  
 			   - Экономикалық экстремизм** экономикалық мақсаттарға жету үшін зорлық-зомбылық қолдануды қамтиды.  
 			   - Әлеуметтік экстремизм** әлеуметтік тәртіпті өзгертуге немесе теңсіздікті жоюға бағытталған зорлық-зомбылықпен байланысты.  
 			   - Жастар экстремизмі** көбінесе ксенофобия немесе вандализм себепті жастар жасаған зорлық-зомбылықты қамтиды.  
 			   - Экологиялық экстремизм** қоршаған ортаны қорғау мақсатында, мысалы, орманды кесуге қарсы наразылықтар кезінде зорлық-зомбылық қолдануды білдіреді.  

			Мәтін:
			'''
		error_msg = 'Сервер шамадан тыс жүктелген'
	
	try:
		response = client.chat.completions.create(model=engine,
                                       messages=[{"role": "system", "content": system_msg},
                                       {"role": "user", "content": f'{prompt}\n{message}'}])
		return response.choices[0].message.content
	except Exception as e:
		return e
