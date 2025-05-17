import streamlit as st
import os
import tempfile
import subprocess
from groq import Groq

# ========== CONFIGURATION ==========
class CodeStandardizerApp:
    def __init__(self):
        # ========== API CLIENT SETUP ==========
        self.client = Groq(api_key=st.secrets["GROK_API_KEY"])
        self.supported_languages = ["python", "javascript", "java", "C", "C++"]

    st.set_page_config(page_title="🛠️ Code Standardizer & Tester", layout="wide")
    st.title("🧠 Grok Code Standardizer & 🧪 Test Runner")

    # ========== CLEAN CODE FROM LLM ==========
    def clean_code_block(self, code: str) -> str:
        """Strip code block markers (e.g. ```python ... ```) from LLM responses."""
        if code.startswith("```"):
            lines = code.strip().splitlines()
            if lines[0].strip("`").lower() == self.supported_languages.lower():
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            return "\n".join(lines)
        return code

    # ========== CALL LLM ==========
    def call_llm(self, system_prompt, user_code, coding_doc=None, user_prompt=None):
        full_user_prompt = ""

        if coding_doc:
            full_user_prompt += f"### Coding standards:\n{coding_doc}\n\n"
        if user_prompt:
            full_user_prompt += f"{user_prompt}\n\n"

        full_user_prompt += f"### User code in {self.supported_languages}:\n{user_code}\n\n"

        full_user_prompt += f"""
                            You are a professional software engineer. You will be provided with code in {self.supported_languages} and optionally coding standards. 
                            Your task is to generate standardized code and/or test cases.

                            Instructions:
                            1. Return only {self.supported_languages} code. No markdown, no extra text.
                            2. If coding standards are provided, follow them strictly.
                            3. Ensure the code can run without modification.
                            """

        try:
            response = self.client.chat.completions.create(
                model="meta-llama/llama-4-scout-17b-16e-instruct",
                messages=[{"role": "user", "content": full_user_prompt}],
                temperature=1,
                max_completion_tokens=1024,
                top_p=1,
                stream=False,
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"❌ LLM API Error: {e}")
            return ""

    # ========== EXECUTE TESTS ==========
    def run_tests(self, code_str: str, test_str: str) -> str:
        with tempfile.TemporaryDirectory() as temp_dir:
            if self.supported_languages.lower() == "python":
                code_path = os.path.join(temp_dir, "main.py")
                test_path = os.path.join(temp_dir, "test_main.py")

                with open(code_path, "w") as f:
                    f.write(code_str)
                with open(test_path, "w") as f:
                    f.write(test_str)

                result = subprocess.run(["python", test_path], capture_output=True, text=True)
                return result.stdout + result.stderr

            elif self.supported_languages.lower() == "javascript":
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
                return f"❌ Language '{self.supported_languages}' is not supported yet."

    # ========== UI ==========
    def render_app(self):
        with st.sidebar:
            st.header("⚙️ Settings")
            language = st.selectbox("Select Programming Language", self.supported_languages)
            system_prompt = st.text_area("🧾 System Prompt", height=150)
            user_prompt = st.text_area("✍️ Optional User Prompt", height=100)
            uploaded_file = st.file_uploader("📄 Upload Coding Standards (optional)", type=["txt", "md", "pdf"])

        st.markdown("This app standardizes your code and optionally generates test cases using **Grok (LLaMA 4)**.")

        user_code = st.text_area("📥 Paste your code here:", height=200)

        coding_doc_content = None
        if uploaded_file:
            try:
                coding_doc_content = uploaded_file.read().decode("utf-8")
            except:
                st.error("❌ Could not read uploaded file. Please use a text-based format.")

        # === Main Workflow Buttons ===
        col1, col2 = st.columns(2)

        if col1.button("🔧 Standardize Code"):
            if not user_code or not system_prompt:
                st.warning("⚠️ Please provide both code and system prompt.")
            else:
                raw_code = self.call_llm(system_prompt, user_code, language, coding_doc=coding_doc_content, user_prompt=user_prompt)
                clean_code = self.clean_code_block(raw_code, language)
                st.session_state["standardized_code"] = clean_code

                st.subheader("🧼 Standardized Code")
                st.code(clean_code, language=language)

        if col2.button("🧪 Generate & Run Tests"):
            if "standardized_code" not in st.session_state:
                st.warning("⚠️ Please generate the standardized code first.")
            else:
                test_prompt = f"Generate test cases in {language} to validate the functionality of the following code:\n\n" \
                            f"{st.session_state['standardized_code']}"
                raw_tests = self.call_llm(system_prompt, st.session_state["standardized_code"], language, user_prompt=test_prompt)
                clean_tests = self.clean_code_block(raw_tests, language)

                st.subheader("🧪 Test Cases")
                st.code(clean_tests, language=language)

                st.subheader("📊 Test Execution Report")
                result = self.run_tests(st.session_state["standardized_code"], clean_tests, language)
                st.text(result)

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