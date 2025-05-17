import streamlit as st
import os
import tempfile
import subprocess
from groq import Groq
import re


class CodeStandardizerApp:
    def __init__(self):
        self.client = Groq(api_key=st.secrets["GROK_API_KEY"])
        self.supported_languages = ["python", "javascript"]

    def login(self):
        st.title("🔐 Secure Code Access")
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input("Password", type="password", placeholder="Enter your password")

        if st.button("Login"):
            if email and password:
                st.session_state["logged_in"] = True
                st.session_state["user_email"] = email
                st.rerun()
            else:
                st.warning("Please enter both email and password.")

    def clean_llm_output(self, code: str, language: str) -> str:
        # Remove language header like ```python or ```javascript
        return re.sub(r"^```[a-zA-Z]+\n?|```$", "", code.strip(), flags=re.MULTILINE)

    def call_llm(self, system_prompt, user_code, language, coding_doc=None, user_prompt=None):
        full_user_prompt = ""
        if coding_doc:
            full_user_prompt += f"Coding standards:\n{coding_doc}\n\n"
        if user_prompt:
            full_user_prompt += f"{user_prompt}\n\n"

        full_user_prompt += f"Here is the user code:\n{user_code}\n\n"
        full_user_prompt += (
            f"""
You are a professional {language} developer. You will receive a piece of code and optionally some organizational coding standards. 
Your task is to:
1. Standardize the code according to best practices or the provided guidelines.
2. Generate test cases for the standardized code in the same language.

Your response must be a JSON with exactly two keys:
- "standardized_code"
- "test_cases"

Do not include explanations or other formatting.
"""
        )

        try:
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": full_user_prompt},
                ],
                temperature=1,
                max_completion_tokens=2048,
                top_p=1,
                stream=False,
            )

            return response.choices[0].message.content
        except Exception as e:
            st.error(f"❌ Error calling Groq API: {e}")
            return '{"standardized_code": "", "test_cases": ""}'

    def run_tests(self, code_str: str, test_str: str, language: str) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            if language.lower() == "python":
                code_path = os.path.join(temp_dir, "main.py")
                test_path = os.path.join(temp_dir, "test_main.py")

                with open(code_path, "w") as f:
                    f.write(code_str)
                with open(test_path, "w") as f:
                    f.write(test_str)

                result = subprocess.run(["python", test_path], capture_output=True, text=True)
                return result.stdout + result.stderr

            elif language.lower() == "javascript":
                code_path = os.path.join(temp_dir, "main.js")
                test_path = os.path.join(temp_dir, "test_main.js")

                with open(code_path, "w") as f:
                    f.write(code_str)
                with open(test_path, "w") as f:
                    f.write(f"const {{ fibonacci }} = require('./main');\n\n")
                    f.write(test_str)

                result = subprocess.run(["node", test_path], capture_output=True, text=True)
                return result.stdout + result.stderr
            else:
                return f"❌ Language '{language}' is not supported yet."

    def render_app(self):
        st.title("🤖 Grok Code Standardizer & Test Generator")
        st.markdown("Uses LLM to clean up your code and generate test cases!")

        language = st.selectbox("Select programming language", self.supported_languages)
        user_code = st.text_area("Paste your code:", height=200)
        system_prompt = st.text_area("Enter system/system message for standardization:", height=100)
        user_prompt = st.text_area("Optional user prompt or instruction:", height=100)

        uploaded_file = st.file_uploader("Upload coding standard document (optional)", type=["txt", "md", "pdf"])
        coding_doc_content = None
        if uploaded_file:
            try:
                coding_doc_content = uploaded_file.read().decode("utf-8")
            except:
                st.error("❌ Could not read the uploaded file.")

        if st.button("⚙️ Standardize Code & Generate Tests"):
            if not user_code or not system_prompt:
                st.warning("⚠️ Please fill in both user code and system prompt.")
                return

            llm_response = self.call_llm(system_prompt, user_code, language, coding_doc_content, user_prompt)

            try:
                parsed_response = eval(llm_response)
                code = self.clean_llm_output(parsed_response["standardized_code"], language)
                tests = self.clean_llm_output(parsed_response["test_cases"], language)

                st.subheader("🧼 Standardized Code")
                st.code(code, language=language)

                st.subheader("🧪 Generated Test Cases")
                st.code(tests, language=language)

                if st.button("🚀 Run Tests"):
                    result = self.run_tests(code, tests, language)
                    st.subheader("📊 Test Execution Output")
                    st.text(result)

            except Exception as e:
                st.error("❌ Failed to parse LLM output. Make sure the model returns a JSON with 'standardized_code' and 'test_cases'.")
                st.code(llm_response)

    def run(self):
        if "logged_in" not in st.session_state:
            st.session_state["logged_in"] = False

        if not st.session_state["logged_in"]:
            self.login()
        else:
            self.render_app()


# Run the app
if __name__ == "__main__":
    app = CodeStandardizerApp()
    app.run()