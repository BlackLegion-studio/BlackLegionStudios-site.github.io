import os
import sys
import glob
import json
from azure.ai.inference import ChatCompletionsClient
from azure.ai.inference.models import SystemMessage, UserMessage
from azure.core.credentials import AzureKeyCredential

def get_codebase_summary():
    """Собирает кодовую базу в один текст с номерами строк"""
    context = []
    # Добавили LICENSE, чтобы робот мог читать лицензию проекта
    extensions = ['*.js', '*.py', '*.ts', '*.json', '*.md', '*.yml', '*.yaml', '*.html', 'LICENSE']
    
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
                
    # Защита: если кодовая база пустая, возвращаем заглушку, чтобы ИИ не падал
    if not context:
        return "В репозитории пока нет файлов с кодом."
    return "\n".join(context)

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Ошибка: GITHUB_TOKEN не найден.")
        sys.exit(1)

    try:
        client = ChatCompletionsClient(
            endpoint="https://azure.com",
            credential=AzureKeyCredential(token)
        )
    except Exception as e:
        print(f"Ошибка инициализации клиента: {e}")
        sys.exit(1)
    
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
        "   ```\n   // Путь: название_файла.ext\n   строка_кода_с_номером\n   ```\n"
        "2. Кратко и понятно объясни логику работы этой части кода.\n"
        "3. Если в коде нет временно ответа, честно скажи об этом."
    )

    user_prompt = f"КОД ПРОЕКТА:\n{codebase}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{full_question}"

    try:
        response = client.complete(
            messages=[
                SystemMessage(content=system_prompt),
                UserMessage(content=user_prompt)
            ],
            model="gpt-4o",
            temperature=0.2
        )
        ai_answer = response.choices.message.content
    except Exception as e:
        print(f"Ошибка запроса к ИИ: {e}")
        sys.exit(1)

    # Запись комментария в файл
    comment_file = "comment.json"
    with open(comment_file, "w", encoding="utf-8") as f:
        json.dump({"body": ai_answer}, f)
        
    issue_number = os.getenv("ISSUE_NUMBER")
    
    # Пытаемся отправить комментарий
    exit_code = os.system(f"gh issue comment {issue_number} --body-file {comment_file}")
    if exit_code != 0:
        print("Ошибка отправки комментария через GitHub CLI. Проверьте Workflow Permissions в настройках!")
        sys.exit(1)

if __name__ == "__main__":
    main()
 
