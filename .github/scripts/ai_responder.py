import os
import sys
import glob
import json
import subprocess
import urllib.request

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

    # Формируем промпт для Copilot
    system_prompt = (
        "Ты официальный ИИ-ассистент этого репозитория. Отвечай строго на русском языке. "
        "Проанализируй вопрос пользователя и код проекта. Дай точный ответ, посчитай если просят, "
        "если нужно — процитируй кусок кода. Будь дружелюбным ботом."
    )
    
    full_prompt = f"{system_prompt}\n\nКОД ПРОЕКТА:\n{codebase}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{full_question}"

    print("Запрос отправляется во встроенный GitHub Copilot...")
    
    # Активируем встроенный в GitHub Actions ИИ-инструмент через консоль
    try:
        # Устанавливаем расширение copilot для консоли, если его нет
        subprocess.run("gh extension install github/gh-copilot --force", shell=True, check=True)
        
        # Передаем наш текст напрямую в официальный ИИ Гитхаба
        process = subprocess.Popen(
            ["gh", "copilot", "explain", full_prompt],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        stdout, stderr = process.communicate()
        
        if process.returncode != 0 or not stdout.strip():
            # Запасной вариант, если утилита explain перегружена
            process = subprocess.Popen(
                ["gh", "copilot", "suggest", "-t", "shell", full_prompt],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding="utf-8"
            )
            stdout, stderr = process.communicate()
            
        ai_answer = stdout.strip() if stdout.strip() else "Извините, не удалось получить ответ от встроенного ИИ."
    except Exception as e:
        ai_answer = f"Ошибка вызова встроенного ИИ GitHub: {e}"

    # Публикуем официальный ответ через API от имени бота github-actions[bot]
    repo = os.getenv("GITHUB_REPOSITORY")
    issue_number = os.getenv("ISSUE_NUMBER")
    url = f"https://github.com{repo}/issues/{issue_number}/comments"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "GitHub-Actions"
    }
    
    data = json.dumps({"body": ai_answer}).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    
    try:
        with urllib.request.urlopen(req) as resp:
            print("Комментарий успешно опубликован фиолетовым ботом!")
    except Exception as e:
        print(f"Ошибка отправки через API: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

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
 
