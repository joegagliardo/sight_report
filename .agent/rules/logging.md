---
trigger: always_on
---

# Prompt Logging Rule
Whenever I give you a new task or prompt, you must:
1. Append the full text of the prompt to a file in the project root named `PROMPT_HISTORY.log`.
2. Include a timestamp and the current branch name.
3. Do this silently as the first step of every task before you begin planning or coding.