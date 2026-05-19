import os
import sys
import glob
import json
# Используем встроенную библиотеку для моделей GitHub
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

def get_codebase_summary():
    """Собирает кодовую базу в один текст с номерами строк"""
    context = []
    # Добавьте сюда расширения файлов вашего проекта, если нужно
    extensions = ['*.js', '*.py', '*.ts', '*.json', '*.md', '*.yml', '*.yaml', '*.html']
    
    for ext in extensions:
        for filename in glob.glob(f'**/{ext}', recursive=True):
            if any(p in filename for p in ['.github/scripts', 'node_modules', '.git', 'package-lock.json']):
                continue
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    file_content = "".join([f"{i+1}: {line}" for i, line in enumerate(lines)])
                    context.append(f"--- ФАЙЛ: {filename} ---\n{file_content}\n")
            except Exception:
                pass
    return "\n".join(context)

def main():
    # Токен GitHub автоматически подставляется системой
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Ошибка: GITHUB_TOKEN не найден.")
        return

    # Подключаемся к бесплатному маркетплейсу моделей GitHub
    client = ChatCompletionsClient(
        endpoint="https://azure.com",
        credential=AzureKeyCredential(token)
    )
    
    title = os.getenv("QUESTION_TITLE", "")
    body = os.getenv("QUESTION_BODY", "")
    full_question = f"Заголовок: {title}\nТекст вопроса: {body}"
    
    codebase = get_codebase_summary()

    system_prompt = (
        "Ты — ИИ-ассистент этого репозитория. Отвечай строго на русском языке.\n"
        "Твоя задача — изучить код проекта и ответить на вопрос пользователя.\n"
        "Правила ответа:\n"
        "1. Найди в предоставленном коде ответ. Если он есть, ОБЯЗАТЕЛЬНО процитируй кусок кода с указанием пути к файлу.\n"
        "   Формат цитаты:\n"
        "   ```язык\n   // Путь: название_файла.ext\n   строка_кода_с_номером\n   ```\n"
        "2. Кратко и понятно объясни логику работы этой части кода.\n"
        "3. Если в коде нет ответа или функционал не реализован, честно ответь: "
        "'В текущем коде проекта этого нет или это не реализовано' и предложи базовое решение."
    )

    user_prompt = f"КОД ПРОЕКТА:\n{codebase}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{full_question}"

    # Бесплатно вызываем самую мощную модель gpt-4o из каталога GitHub
    response = client.complete(
        messages=[
            SystemMessage(content=system_prompt),
            UserMessage(content=user_prompt)
        ],
        model="gpt-4o",
        temperature=0.2
    )
    
    ai_answer = response.choices[0].message.content

    # Публикуем комментарий в ветку обсуждения (Issue) через встроенную утилиту gh
    issue_number = os.getenv("ISSUE_NUMBER")
    comment_file = "comment.json"
    with open(comment_file, "w", encoding="utf-8") as f:
        json.dump({"body": ai_answer}, f)
        
    os.system(f"gh issue comment {issue_number} --body-file {comment_file}")

if __name__ == "__main__":
    main()
