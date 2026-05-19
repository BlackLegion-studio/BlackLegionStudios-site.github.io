import os
import sys
import glob
import subprocess
import json
import urllib.request

def get_codebase_summary():
    """Собирает кодовую базу репозитория в единый контекст для ИИ"""
    context = []
    extensions = ['*.js', '*.py', '*.ts', '*.json', '*.md', '*.yml', '*.yaml', '*.html', 'LICENSE', '.gitignore']
    for ext in extensions:
        for filename in glob.glob(f'**/{ext}', recursive=True):
            if any(p in filename for p in ['.github/scripts', 'node_modules', '.git/', 'package-lock.json']):
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

def ask_github_llm(token, system_prompt, user_prompt):
    """Использует встроенный БЕСПЛАТНЫЙ ИИ от GitHub (Модель GPT-4o-mini). Ключ не нужен!"""
    # Этот эндпоинт встроен в инфраструктуру GitHub Actions и доступен по вашему GITHUB_TOKEN
    url = "https://azure.com"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "model": "gpt-4o-mini", # Отличная бесплатная модель для кодинга
        "temperature": 0.2,
        "max_tokens": 4096
    }
    
    req = urllib.request.Request(url, data=json.dumps(data).encode('utf-8'), headers=headers)
    
    try:
        with urllib.request.urlopen(req) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            return res_data['choices']['message']['content']
    except Exception as e:
        return f"❌ Ошибка встроенного ИИ: {e}. Проверьте, включен ли доступ в репозитории."

def main():
    # Берем тот самый токен, который GitHub Actions выдает вашей сборке автоматически
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Ошибка: GITHUB_TOKEN не найден.")
        sys.exit(1)

    issue_number = os.getenv("ISSUE_NUMBER")
    if not issue_number:
        print("Ошибка: ISSUE_NUMBER не задан.")
        sys.exit(1)

    title = os.getenv("QUESTION_TITLE", "")
    body = os.getenv("QUESTION_BODY", "")
    
    # Собираем контекст вашего проекта
    codebase = get_codebase_summary()
    
    system_prompt = (
        "Ты — опытный ИИ-программист. Твоя цель — писать, дополнять и исправлять код для пользователя. "
        "Тебе дан текущий код проекта (файлы и строки). Пиши новые функции так, чтобы они подходили под архитектуру. "
        "Отвечай строго по делу, присылай готовый к копированию код в Markdown-блоках с указанием языка."
    )
    
    user_prompt = (
        f"Текущий проект:\n\n{codebase}\n\n"
        f"--- ЗАДАНИЕ ---\n"
        f"Тема: {title}\n"
        f"Что нужно сделать:\n{body}\n"
    )
    
    print("Запрос отправлен во встроенный ИИ GitHub...")
    ai_raw_response = ask_github_llm(token, system_prompt, user_prompt)
    
    ai_answer = (
        f"🤖 **Локальный ИИ-разработчик:**\n\n"
        f"{ai_raw_response}"
    )

    comment_file = "bot_comment.txt"
    with open(comment_file, "w", encoding="utf-8") as f:
        f.write(ai_answer)
        
    print("Публикация ответа в Issue...")
    result = subprocess.run(
        ["gh", "issue", "comment", issue_number, "--body-file", comment_file],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        print(f"Ошибка отправки: {result.stderr}")
        sys.exit(1)
        
    print("Готово!")

if __name__ == "__main__":
    main()
