import os
import sys
import glob
from openai import OpenAI

def get_codebase_summary():
    """Собирает все текстовые файлы кода в один структурированный контекст для ИИ"""
    context = []
    # Ищем файлы кода. Добавьте расширения ваших файлов (например, *.py, *.js, *.go)
    extensions = ['*.js', '*.py', '*.ts', '*.json', '*.md', '*.txt', '*.sh']
    
    for ext in extensions:
        # Ищет файлы даже в глубоких подпапках, игнорируя системные папки
        for filename in glob.glob(f'**/{ext}', recursive=True):
            if '.github' in filename or 'node_modules' in filename or '.git' in filename:
                continue
            try:
                with open(filename, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    # Форматируем файл с номерами строк для удобства цитирования
                    file_content = "".join([f"{i+1}: {line}" for i, line in enumerate(lines)])
                    context.append(f"--- ФАЙЛ: {filename} ---\n{file_content}\n")
            except Exception:
                pass
    return "\n".join(context)

def main():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Пропущено: Нет токена OPENAI_API_KEY в Secrets.")
        return

    client = OpenAI(api_key=api_key)
    
    # Собираем данные о вопросе
    title = os.getenv("QUESTION_TITLE", "")
    body = os.getenv("QUESTION_BODY", "")
    full_question = f"Заголовок: {title}\nТекст вопроса: {body}"
    
    # Сканируем весь код проекта
    codebase = get_codebase_summary()

    # Формируем жесткую системную инструкцию для ИИ
    system_prompt = (
        "Ты — эксперт-инженер проекта. Твоя задача — отвечать на вопросы пользователей по коду.\n"
        "Правила ответа:\n"
        "1. Проанализируй весь предоставленный код проекта.\n"
        "2. Определи, есть ли в коде (или комментариях к нему) ответ на этот вопрос.\n"
        "3. Если ответ есть, ОБЯЗАТЕЛЬНО процитируй кусок кода в формате:\n"
        "   ```язык\n   // Путь к файлу: название_файла.ext\n   строка_кода\n   ```\n"
        "4. Дай краткое, понятное пояснение человеку на русском языке.\n"
        "5. Если в коде нет ответа, прямо ответь: 'В текущем коде проекта этого нет или это не реализовано', и кратко подскажи, куда смотреть."
    )

    user_prompt = f"КОДБЕЙЗ ПРОЕКТА:\n{codebase}\n\nВОПРОС ПОЛЬЗОВАТЕЛЯ:\n{full_question}"

    # Запрос к нейросети (используем gpt-4o для сложного анализа кода)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.2
    )
    
    ai_answer = response.choices[0].message.content

    # Публикуем ответ обратно в GitHub Issue / Комментарий
    issue_number = os.getenv("ISSUE_NUMBER")
    repo = os.getenv("GITHUB_REPOSITORY")
    
    # Используем утилиту curl через GitHub CLI (gh), которая уже встроена в GitHub Actions
    comment_file = "comment.json"
    with open(comment_file, "w", encoding="utf-8") as f:
        import json
        json.dump({"body": ai_answer}, f)
        
    os.system(f"gh issue comment {issue_number} --body-file {comment_file}")

if __name__ == "__main__":
    main()
