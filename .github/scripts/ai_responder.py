import os
import sys
import glob

def get_codebase_summary():
    """Собирает кодовую базу в один текст с номерами строк"""
    context = []
    # Добавили .gitignore в список разрешенных расширений
    extensions = ['*.js', '*.py', '*.ts', '*.json', '*.md', '*.yml', '*.yaml', '*.html', 'LICENSE', '.gitignore']
    for ext in extensions:
        for filename in glob.glob(f'**/{ext}', recursive=True):
            # Теперь игнорируем ТОЛЬКО папку со скриптами, а не всю .github!
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

def main():
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("Ошибка: GITHUB_TOKEN не найден.")
        sys.exit(1)

    title = os.getenv("QUESTION_TITLE", "")
    body = os.getenv("QUESTION_BODY", "")
    full_question = (f"{title} {body}").lower()
    
    # Ищем файлы по всему репозиторию на любую глубину
    all_files = glob.glob('**/*', recursive=True)
    found_file_path = None
    found_file_name = None

    for file_path in all_files:
        if os.path.isdir(file_path) or ".git/" in file_path or ".github/scripts" in file_path:
            continue
        base_name = os.path.basename(file_path).lower()
        
        # Если имя файла (например, .gitignore) упомянуто в вопросе
        if base_name in full_question and base_name != "":
            found_file_path = file_path
            found_file_name = os.path.basename(file_path)
            break

    # Если нашли файл в нашей глубокой структуре
    if found_file_path:
        try:
            with open(found_file_path, 'r', encoding='utf-8') as f:
                first_lines = "".join(f.readlines()[:15])
            
            ai_answer = (
                f"🤖 **Я локальный ИИ-помощник репозитория (Защищенный режим).**\n\n"
                f"Файл успешно обнаружен в секретной папке!\n"
                f"Настоящий путь к нему: `{found_file_path}`.\n\n"
                f"```text\n// Содержимое файла {found_file_name}:\n{first_lines}\n```\n"
                f"Я смог раскопать этот путь локально!"
            )
        except Exception as e:
            ai_answer = f"🤖 Файл `{found_file_name}` найден по пути `{found_file_path}`, но не удалось его прочесть: {e}"
            
    else:
        codebase = get_codebase_summary()
        ai_answer = (
            f"🤖 **ИИ-помощник:** Я просканировал репозиторий, но не нашёл упоминания такого файла.\n\n"
            f"Убедитесь, что вы правильно написали его имя (например, `.gitignore`).\n"
            f"Всего в доступных файлах сейчас {len(codebase.splitlines())} строк текста."
        )

    # Сохраняем как ЧИСТЫЙ ТЕКСТ
    comment_file = "bot_comment.txt"
    with open(comment_file, "w", encoding="utf-8") as f:
        f.write(ai_answer)
        
    issue_number = os.getenv("ISSUE_NUMBER")
    
    print("Отправка чистого текста через ядро GitHub CLI...")
    exit_code = os.system(f"gh issue comment {issue_number} --body-file {comment_file}")
    
    if exit_code != 0:
        sys.exit(1)

if __name__ == "__main__":
    main()
