import os
import sys
import glob
import json
import urllib.request
import urllib.error

def get_codebase_summary():
    """Собирает кодовую базу в один текст с номерами строк"""
    context = []
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
    if not context:
        return "В репозитории пока нет файлов с кодом."
    return "\n".join(context)

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Ошибка: GITHUB_TOKEN не найден.")
        sys.exit(1)

    title = os.getenv("QUESTION_TITLE", "")
    body = os.getenv("QUESTION_BODY", "")
    full_question = f"Заголовок: {title}\nТекст вопроса: {body}"
    codebase = get_codebase_summary()

    system_prompt = (
        "Ты официальный ИИ-ассистент этого репозитория. Отвечай строго на русском языке.\n"
        "Проанализируй вопрос пользователя и код проекта. Дай точный ответ, посчитай если просят, "
        "если нужно — процитируй кусок кода. Будь дружелюбным ботом."
    )
    
    # 1. Запрос к официальному бесплатному ИИ Гитхаба (Модель GPT-4o)
    ai_url = "https://azure.com"
    ai_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    ai_data = json.dumps({
        "model": "gpt-4o",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"КОД ПРОЕКТА:\n{codebase}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{full_question}"}
        ],
        "temperature": 0.2
    }).encode("utf-8")

    print("Запрос к ИИ-серверу GitHub...")
    req_ai = urllib.request.Request(ai_url, data=ai_data, headers=ai_headers, method="POST")
    
    try:
        with urllib.request.urlopen(req_ai) as response:
            res = json.loads(response.read().decode("utf-8"))
            ai_answer = res["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        ai_answer = f"Ошибка ИИ-сервера (HTTP {e.code}). Перезапустите воркфлоу позже."
    except Exception as e:
        ai_answer = f"Не удалось связаться с ИИ-сервером: {e}"

    # 2. Публикация ответа в ваш Issue (от имени фиолетового робота github-actions)
    repo = os.getenv("GITHUB_REPOSITORY")
    issue_number = os.getenv("ISSUE_NUMBER")
    github_api_url = f"https://github.com{repo}/issues/{issue_number}/comments"
    
    github_headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Actions"
    }
    
    github_data = json.dumps({"body": ai_answer}).encode("utf-8")
    req_github = urllib.request.Request(github_api_url, data=github_data, headers=github_headers, method="POST")
    
    print("Отправка комментария в GitHub...")
    try:
        with urllib.request.urlopen(req_github) as resp:
            print("Успех! Комментарий опубликован.")
    except Exception as e:
        print(f"Ошибка отправки в ветку GitHub: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
