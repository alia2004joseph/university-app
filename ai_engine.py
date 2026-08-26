"""
ai_engine.py — Multi-provider AI engine for Smart University App.

Features:
  1. Gemini multi-key rotation (quota safe)
  2. Fallback to Groq, Mistral, HuggingFace, Cloudflare
  3. PDF content cached 1 hour
  4. Per-student cooldown (30s)
  5. Strict academic system prompts
  6. AIStudyAssistant for students
  7. AIRepAssistant for Class Rep dashboard
  8. AISortingEngine for group allocation
"""

import time
import os
import re
import io
import subprocess
import tempfile
import streamlit as st
import requests
import fitz  # PyMuPDF
import pandas as pd
import json
from urllib.parse import quote
from PIL import Image, ImageDraw
from google import genai
from google.genai import types

# ── IMPORT IMAGE GENERATOR ──
from image_generator import generate_image  # ✅ This is the ONLY source of generate_image

# ─────────────────────────────────────────────
# MODEL CONFIGURATION
# ─────────────────────────────────────────────
CACHE_DIR = ".image_cache"
STUDENT_MODEL = "models/gemini-2.5-flash"
REP_MODEL = "models/gemini-2.5-flash"
ALLOC_MODEL = "models/gemini-2.5-flash"
STUDENT_COOLDOWN_SECONDS = 30

# ─────────────────────────────────────────────
# SYSTEM PROMPTS
# ─────────────────────────────────────────────
STUDENT_SYSTEM_PROMPT = (
    "You are a dedicated academic study assistant for university students. "
    "Your primary role is to help students understand their uploaded course materials. "
    "When a document is provided, base your answers STRICTLY on that document. "
    "For general academic questions (engineering, physics, mathematics, science), "
    "use your full academic knowledge but keep answers focused on university-level study. "
    "Do NOT answer questions about sports, entertainment, current events, or non-academic topics. "
    "Always give COMPLETE, detailed answers. Use clear structure."
)

REP_SYSTEM_PROMPT = (
    "You are a professional academic administrative assistant for a university Class Representative. "
    "You help the Class Rep manage their duties efficiently: drafting announcements, suggesting replies, "
    "summarizing feedback, formatting timetables, and checking conflicts. "
    "Always be professional, clear, and concise."
)

ADMIN_SYSTEM_PROMPT = (
    "You are an intelligent university administrative assistant helping a Super Admin "
    "manage multiple departments and year groups. "
    "Provide clear, structured, data-driven insights. "
    "Be concise and professional."
)

# ─────────────────────────────────────────────
# CODE FORMATTER HELPER
# ─────────────────────────────────────────────
def format_code_with_black(code: str) -> str:
    """
    Format Python code using the black formatter.
    Falls back to basic indentation fix if black is not available.
    """
    try:
        # Try to use black
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
        
        # Run black formatter
        result = subprocess.run(
            ['black', '--quiet', temp_path],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            with open(temp_path, 'r') as f:
                formatted = f.read()
            os.unlink(temp_path)
            return formatted
        
        # If black failed, clean up and fall back
        os.unlink(temp_path)
        
    except Exception as e:
        print(f"[Formatter] Black not available: {e}")
    
    # ── Fallback: Basic indentation fix ──
    return _basic_indentation_fix(code)

def _basic_indentation_fix(code: str) -> str:
    """
    Basic indentation fixer when black is not available.
    """
    lines = code.splitlines()
    fixed_lines = []
    indent_level = 0
    
    for i, line in enumerate(lines):
        stripped = line.lstrip()
        
        # Skip empty lines
        if not stripped:
            fixed_lines.append('')
            continue
        
        # Calculate current indentation
        current_indent = len(line) - len(stripped)
        
        # Check if this line starts a new block
        block_starters = ['def ', 'class ', 'if ', 'elif ', 'else:', 
                          'for ', 'while ', 'try:', 'except ', 
                          'finally:', 'with ', '@']
        
        if any(stripped.startswith(x) for x in block_starters):
            # This is a block starter
            if stripped.endswith(':'):
                # If previous line was also a block starter, reduce indent
                if i > 0 and lines[i-1].strip().endswith(':'):
                    indent_level = max(0, indent_level - 1)
                
                # Add the line with current indentation
                fixed_lines.append(' ' * (indent_level * 4) + stripped)
                
                # Increase indentation for next line
                indent_level += 1
                continue
        
        # Handle dedents (else, elif, except, finally)
        if stripped.startswith(('else:', 'elif ', 'except ', 'finally:')):
            indent_level = max(0, indent_level - 1)
            fixed_lines.append(' ' * (indent_level * 4) + stripped)
            # If this ends with ':', increase indent for next line
            if stripped.endswith(':'):
                indent_level += 1
            continue
        
        # Add the line with proper indentation
        # Check if we need to maintain indentation from previous line
        if i > 0 and lines[i-1].strip().endswith(':') and current_indent == 0:
            # Previous line was a block starter and this line has no indent
            fixed_lines.append(' ' * (indent_level * 4) + stripped)
        else:
            fixed_lines.append(' ' * (indent_level * 4) + stripped)
    
    return '\n'.join(fixed_lines)

def validate_and_fix_code(code: str, filename: str = "temp.py") -> tuple[bool, str, list]:
    """
    Validate Python code syntax and attempt to fix common issues.
    Returns (is_valid, fixed_code, errors)
    """
    errors = []
    fixed_code = code
    
    # First, try to fix indentation
    fixed_code = _basic_indentation_fix(fixed_code)
    
    # Check syntax
    try:
        compile(fixed_code, filename, "exec")
        return True, fixed_code, []
    except SyntaxError as e:
        errors.append(f"Line {e.lineno}: {e.msg}")
        
        # Try to fix specific errors
        if "expected an indented block" in e.msg:
            # Add 'pass' to empty blocks
            lines = fixed_code.splitlines()
            if e.lineno <= len(lines):
                # Find the line with the error
                error_line = lines[e.lineno - 1]
                if ':' in error_line:
                    # Add pass as the next line
                    indent = len(error_line) - len(error_line.lstrip())
                    lines.insert(e.lineno, ' ' * (indent + 4) + 'pass')
                    fixed_code = '\n'.join(lines)
                    
                    # Check again
                    try:
                        compile(fixed_code, filename, "exec")
                        return True, fixed_code, []
                    except SyntaxError as e2:
                        errors.append(f"Still has error: {e2.msg}")
                        return False, fixed_code, errors
        
        return False, fixed_code, errors

# ─────────────────────────────────────────────
# GEMINI KEY ROTATION MANAGER
# ─────────────────────────────────────────────
class KeyRotationManager:
    def __init__(self):
        self.keys = self._load_keys()
        self.current_index = 0

    def _load_keys(self) -> list:
        keys = []
        for i in range(1, 10):
            k = ""
            try:
                k = (st.secrets.get(f"GEMINI_KEY_{i}", "") if hasattr(st, "secrets") else "") or (st.secrets.get(f"GEMINI_API_KEY_{i}", "") if hasattr(st, "secrets") else "")
            except Exception:
                pass
            if not k:
                k = os.environ.get(f"GEMINI_KEY_{i}", "") or os.environ.get(f"GEMINI_API_KEY_{i}", "")
            if k and k not in keys:
                keys.append(k.strip())
        if not keys:
            k = ""
            try:
                k = (st.secrets.get("GEMINI_API_KEY", "") if hasattr(st, "secrets") else "") or (st.secrets.get("GEMINI_KEY", "") if hasattr(st, "secrets") else "")
            except Exception:
                pass
            if not k:
                k = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GEMINI_KEY", "")
            if k and k not in keys:
                keys.append(k.strip())
        return keys

    def get_client(self):
        if not self.keys:
            return None
        return genai.Client(api_key=self.keys[self.current_index])

    def rotate(self):
        if self.keys:
            self.current_index = (self.current_index + 1) % len(self.keys)

    def total_keys(self) -> int:
        return len(self.keys)

    def has_keys(self) -> bool:
        return len(self.keys) > 0


_key_manager = KeyRotationManager()

# ─────────────────────────────────────────────
# PROVIDER HELPERS
# ─────────────────────────────────────────────
def try_gemini(model, contents, config):
    client = _key_manager.get_client()
    return client.models.generate_content(model=model, contents=contents, config=config).text


def try_groq(contents, api_key):
    resp = requests.post(
        "https://api.groq.com/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "mixtral-8x7b", "messages": [{"role": "user", "content": contents}]}
    )
    return resp.json()["choices"][0]["message"]["content"]


def try_mistral(contents, api_key):
    resp = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={"Authorization": f"Bearer {api_key}"},
        json={"model": "mistral-medium", "messages": [{"role": "user", "content": contents}]}
    )
    return resp.json()["choices"][0]["message"]["content"]


def try_huggingface(contents, token):
    resp = requests.post(
        "https://api-inference.huggingface.co/models/bigscience/bloom",
        headers={"Authorization": f"Bearer {token}"},
        json={"inputs": contents}
    )
    return resp.json()[0]["generated_text"]


def try_cloudflare(contents, token, account_id):
    resp = requests.post(
        f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/@cf/meta/llama-2-7b-chat-int8",
        headers={"Authorization": f"Bearer {token}"},
        json={"messages": [{"role": "user", "content": contents}]}
    )
    return resp.json()["result"]["response"]


# ─────────────────────────────────────────────
# FALLBACK MANAGER
# ─────────────────────────────────────────────
def _call_with_retry(model: str, contents: str, config) -> str:
    # ── Try ALL Gemini keys in rotation ─────────────────────
    if _key_manager.has_keys():
        for attempt in range(_key_manager.total_keys()):
            try:
                return try_gemini(model, contents, config)
            except Exception as e:
                err = str(e)
                if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                    print(f"[Gemini key {_key_manager.current_index}] Quota hit, rotating...")
                    _key_manager.rotate()
                    continue
                else:
                    print(f"[Gemini error] {e}")
                    break

    # ── Fallback: Groq ───────────────────────────────────────
    groq_key = st.secrets.get("GROQ_API_KEY", "")
    if groq_key:
        try:
            print("[AI] Trying Groq...")
            return try_groq(contents, groq_key)
        except Exception as e:
            print(f"[Groq error] {e}")

    # ── Fallback: Mistral ────────────────────────────────────
    mistral_key = st.secrets.get("MISTRAL_API_KEY", "")
    if mistral_key:
        try:
            print("[AI] Trying Mistral...")
            return try_mistral(contents, mistral_key)
        except Exception as e:
            print(f"[Mistral error] {e}")

    # ── Fallback: HuggingFace ────────────────────────────────
    hf_token = st.secrets.get("HUGGINGFACE_TOKEN", "")
    if hf_token:
        try:
            print("[AI] Trying HuggingFace...")
            return try_huggingface(contents, hf_token)
        except Exception as e:
            print(f"[HF error] {e}")

    # ── Fallback: Cloudflare ─────────────────────────────────
    cf_token = st.secrets.get("CLOUDFLARE_TOKEN", "")
    cf_account = st.secrets.get("CLOUDFLARE_ACCOUNT_ID", "")
    if cf_token and cf_account:
        try:
            print("[AI] Trying Cloudflare...")
            return try_cloudflare(contents, cf_token, cf_account)
        except Exception as e:
            print(f"[Cloudflare error] {e}")

    return "⚠️ All AI providers are currently unavailable. Please check your API keys in secrets.toml."


# ─────────────────────────────────────────────
# PDF TEXT EXTRACTION
# ─────────────────────────────────────────────
@st.cache_data(ttl=3600, show_spinner=False)
def extract_pdf_text(url: str, file_name: str) -> str:
    try:
        response = requests.get(url, timeout=30)
        if response.status_code != 200:
            return ""
        pdf_doc = fitz.open(stream=response.content, filetype="pdf")
        text = "".join([page.get_text() for page in pdf_doc])
        pdf_doc.close()
        return text[:12000].strip()
    except Exception as e:
        print(f"[ai_engine] PDF extract error for {file_name}: {e}")
        return ""


# ─────────────────────────────────────────────────────────────
# AI SORTING ENGINE — Group Allocation
# ─────────────────────────────────────────────────────────────
class AISortingEngine:
    def generate_teams(
        self,
        df_profiles: pd.DataFrame,
        team_size: int,
        instructions: str
    ) -> dict:
        if not _key_manager.has_keys():
            return {"error": "No API keys found in secrets.toml."}
        try:
            clean_roster = df_profiles[
                ["Student Name", "Reg Number", "Course Code"]
            ].to_json(orient="records")

            prompt = (
                f"You are an academic project coordinator. Group the following student list into balanced teams "
                f"of approximately {team_size} members. Mix students from different course codes if possible.\n"
                f"Custom Constraints: {instructions}\n"
                f"Student Data Array: {clean_roster}\n\n"
                f"CRITICAL: Return a valid raw JSON object mapping every student's 'Reg Number' to their group name.\n"
                f"Example: {{\"25/U/0001/PS\": \"Team Alpha\", \"25/U/0002/PS\": \"Team Beta\"}}\n"
            )
            config = types.GenerateContentConfig(response_mime_type="application/json")
            result = _call_with_retry(ALLOC_MODEL, prompt, config)
            if result.startswith("⚠️"):
                return {"error": result}
            return json.loads(result)
        except Exception as e:
            return {"error": str(e)}


# ─────────────────────────────────────────────────────────────
# AI STUDY ASSISTANT — For Students
# ─────────────────────────────────────────────────────────────
class AIStudyAssistant:

    def _check_cooldown(self, student_reg: str) -> tuple[bool, int]:
        key = f"ai_last_request_{student_reg}"
        last_time = st.session_state.get(key, 0)
        elapsed = time.time() - last_time
        if elapsed < STUDENT_COOLDOWN_SECONDS:
            return False, int(STUDENT_COOLDOWN_SECONDS - elapsed)
        return True, 0

    def _record_request(self, student_reg: str):
        st.session_state[f"ai_last_request_{student_reg}"] = time.time()

    def summarize_material(
        self, pdf_text: str, file_name: str, student_reg: str = ""
    ) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if not pdf_text.strip():
            return "⚠️ Could not extract text from this PDF."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds before making another request."
            self._record_request(student_reg)

        prompt = (
            f"Provide a COMPLETE and detailed summary of this document.\n\n"
            f"Structure your response using these sections:\n"
            f"### 1. Main Topic\n"
            f"### 2. Key Concepts\n"
            f"### 3. Important Formulas & Definitions\n"
            f"### 4. Chapter/Section Breakdown\n"
            f"### 5. Study Tips\n\n"
            f"Do NOT repeat the file name or add a title heading — the app already shows it.\n"
            f"Be thorough and complete every section fully.\n\n"
            f"Document content:\n{pdf_text}"
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=6000
        )
        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def ask_ai(
        self,
        question: str,
        chat_history: list,
        pdf_text: str = "",
        file_name: str = "",
        student_reg: str = ""
    ) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        context_block = ""
        if pdf_text.strip():
            context_block = (
                f"Selected material: '{file_name}'.\n"
                f"--- DOCUMENT START ---\n{pdf_text}\n--- DOCUMENT END ---\n\n"
            )
        history_block = ""
        if chat_history:
            for turn in chat_history[-6:]:
                role = "Student" if turn["role"] == "user" else "Assistant"
                history_block += f"{role}: {turn['content']}\n"
            history_block = f"Previous conversation:\n{history_block}\n"

        full_prompt = (
            f"{context_block}{history_block}"
            f"Student question: {question}\n\n"
            f"Provide a COMPLETE answer."
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=6000
        )
        return _call_with_retry(STUDENT_MODEL, full_prompt, config)

    def find_formula(
        self, topic: str, pdf_text: str, file_name: str, student_reg: str = ""
    ) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        prompt = (
            f"From '{file_name}', find ALL formulas related to: '{topic}'.\n"
            f"For each: write formula, define variables, explain usage, give example.\n\n"
            f"Document:\n{pdf_text}"
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.2, max_output_tokens=2000
        )
        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def explain_concept(self, concept: str, student_reg: str = "") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        prompt = (
            f"Explain this concept for a university student:\n\n"
            f"Concept: {concept}\n\n"
            f"1. Simple definition\n2. Detailed explanation\n"
            f"3. Key formulas\n4. Real-world example\n5. Common mistakes\n"
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=4000
        )
        return _call_with_retry(STUDENT_MODEL, prompt, config)

    def chat_with_context(
        self,
        question: str,
        chat_history: list,
        student_context: str,
        pdf_text: str = "",
        file_name: str = "",
        student_reg: str = ""
    ) -> str:
        """
        Context-aware AI chat — knows the student's profile,
        announcements, timetable, materials, feedback and group.
        """
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds before asking again."
            self._record_request(student_reg)

        doc_block = ""
        if pdf_text.strip():
            doc_block = (
                f"\n=== SELECTED MATERIAL: {file_name} ===\n"
                f"{pdf_text[:6000]}\n"
                f"=== END OF MATERIAL ===\n"
            )

        history_block = ""
        if chat_history:
            for turn in chat_history[-6:]:
                role = "Student" if turn["role"] == "user" else "Assistant"
                history_block += f"{role}: {turn['content']}\n"
            history_block = f"\n=== RECENT CONVERSATION ===\n{history_block}\n"

        full_prompt = (
            f"{student_context}"
            f"{doc_block}"
            f"{history_block}"
            f"\n=== STUDENT QUESTION ===\n{question}\n\n"
            f"Answer using the student context above. Be personal, friendly and accurate. "
            f"If the question is about their class data (announcements, timetable, materials, "
            f"group, rep, feedback), answer directly from the context. "
            f"For academic questions, use your full knowledge."
        )
        config = types.GenerateContentConfig(
            system_instruction=(
                "You are a strict academic assistant embedded in a university student portal. "
                "You have full knowledge of the student's profile, timetable, announcements, "
                "materials, feedback status, group members, and class rep details. "
                "Always personalize your responses using the student's name and their specific data. "
                "Never say you lack access to their information — you have it all in context. "
                "For class data questions, answer directly and confidently. "
                "For academic subjects (engineering, mathematics, physics, chemistry, science), "
                "be thorough and educational. "
                "STRICTLY FORBIDDEN: Do NOT answer any questions about sports, football, basketball, "
                "cricket, celebrities, movies, music, social media, politics, news, video games, "
                "or ANY non-academic topic. "
                "If asked about any forbidden topic, respond EXACTLY with: "
                "'I can only help with academic and class-related questions. "
                "Ask me about your timetable, materials, announcements, or coursework.' "
                "No exceptions. No apologies. Just redirect firmly. "
                "Keep all responses clear, structured and mobile-friendly."
            ),
            temperature=0.4, max_output_tokens=6000
        )
        return _call_with_retry(STUDENT_MODEL, full_prompt, config)

    def generate_revision_questions(
        self,
        topic: str,
        pdf_text: str = "",
        file_name: str = "",
        num_questions: int = 10,
        student_reg: str = ""
    ) -> str:
        """Generate revision questions from course material or topic."""
        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds."
            self._record_request(student_reg)

        source = f"from '{file_name}':\n{pdf_text[:6000]}" if pdf_text.strip() else f"on the topic: {topic}"
        prompt = (
            f"Generate {num_questions} university-level revision questions {source}.\n\n"
            f"Include a mix of:\n"
            f"- 4 Multiple choice questions (with 4 options and the correct answer)\n"
            f"- 3 Short answer questions\n"
            f"- 2 Calculation/problem-solving questions (if applicable)\n"
            f"- 1 Essay/explain question\n\n"
            f"For each question, provide the answer or model answer below it.\n"
            f"Number each question clearly."
        )
        config = types.GenerateContentConfig(
            system_instruction=STUDENT_SYSTEM_PROMPT,
            temperature=0.5, max_output_tokens=6000
        )
        return _call_with_retry(STUDENT_MODEL, prompt, config)

    # ── NEW: Image Q&A method ─────────────────────────────────
    def ask_about_image(
        self,
        image_bytes: bytes,
        mime_type: str,
        question: str = "",
        chat_history: list = None,
        student_reg: str = ""
    ) -> str:
        """Analyze an image using Gemini vision with multi-key rotation and proper typing."""
        if not _key_manager.has_keys():
            _key_manager.keys = _key_manager._load_keys()
            if not _key_manager.has_keys():
                return "⚠️ No Gemini API key found. Please set GEMINI_API_KEY in secrets.toml or environment."

        if student_reg:
            ok, wait = self._check_cooldown(student_reg)
            if not ok:
                return f"⏳ Please wait {wait} seconds before making another AI request."
            self._record_request(student_reg)

        # Normalize mime type
        clean_mime = "image/jpeg"
        if mime_type:
            raw_mime = mime_type.lower().split(";")[0].strip()
            if "png" in raw_mime:
                clean_mime = "image/png"
            elif "webp" in raw_mime:
                clean_mime = "image/webp"
            elif "gif" in raw_mime:
                clean_mime = "image/gif"
            elif "jpeg" in raw_mime or "jpg" in raw_mime:
                clean_mime = "image/jpeg"

        # Build image part for google.genai
        try:
            image_part = types.Part.from_bytes(data=image_bytes, mime_type=clean_mime)
        except Exception:
            try:
                image_part = types.Part(inline_data=types.Blob(mime_type=clean_mime, data=image_bytes))
            except Exception:
                import base64
                image_part = {
                    "inline_data": {
                        "mime_type": clean_mime,
                        "data": base64.b64encode(image_bytes).decode("utf-8")
                    }
                }

        q_text = question.strip() if question and question.strip() else (
            "Analyze and explain this image thoroughly for university coursework. "
            "If it contains a diagram, circuit, or graph, explain all components and dynamics. "
            "If it contains equations or a problem, provide full step-by-step mathematical working and solutions. "
            "If it contains lecture notes, summarize the core principles clearly."
        )

        config = types.GenerateContentConfig(
            system_instruction=(
                "You are an expert university academic study tutor and STEM specialist. "
                "Analyze images (diagrams, handwritten notes, textbook pages, graphs, circuit schematics, physics/math problems). "
                "Provide detailed, precise, educational explanations formatted with clear Markdown headings, bullet points, and LaTeX notation where applicable."
            ),
            temperature=0.3,
            max_output_tokens=6000
        )

        contents = [image_part, q_text]

        # Multi-key rotation & fallback model loop
        last_error = ""
        models_to_try = [STUDENT_MODEL, "gemini-2.5-flash", "gemini-2.0-flash", "gemini-1.5-flash"]
        seen_models = []
        for m in models_to_try:
            if m and m not in seen_models:
                seen_models.append(m)

        for attempt in range(max(_key_manager.total_keys(), 1)):
            client = _key_manager.get_client()
            if not client:
                break
            for mdl in seen_models:
                try:
                    response = client.models.generate_content(
                        model=mdl,
                        contents=contents,
                        config=config
                    )
                    if response and response.text:
                        return response.text
                except Exception as e:
                    last_error = str(e)
                    if "429" in last_error or "RESOURCE_EXHAUSTED" in last_error or "quota" in last_error.lower():
                        break
                    continue
            _key_manager.rotate()

        return f"⚠️ Image analysis error: {last_error or 'Could not generate vision response'}\n\n💡 Tip: Verify your GEMINI_API_KEY in secrets.toml or environment variables."

    def answer_group_query(self, student_name: str, query: str, course_groups: dict) -> str:
        """
        Answer student queries about their course-unit groups.
        Example: "What is my thermodynamics group?" or "Which group am I in for mathematics?"
        course_groups format: {"Thermodynamics": "Group A", "Mathematics": "Group B", ...}
        """
        if not _key_manager.has_keys():
            return "I don't have access to group information right now. Please check with your Class Rep."
        
        groups_text = "\n".join([f"- {course}: {group}" for course, group in course_groups.items()])
        
        prompt = (
            f"A student is asking about their course groups. Answer their specific question.\n\n"
            f"Student name: {student_name}\n"
            f"Their course groups:\n{groups_text}\n\n"
            f"Student question: \"{query}\"\n\n"
            f"Answer directly and concisely. If they ask about a specific course, give the exact group name. "
            f"If they ask about all groups, list them all. Be friendly and helpful. Plain text only."
        )
        config = types.GenerateContentConfig(
            system_instruction=(
                "You are a helpful university assistant answering student queries about their course groups. "
                "Be direct, friendly, and accurate."
            ),
            temperature=0.3, max_output_tokens=300
        )
        return _call_with_retry(STUDENT_MODEL, prompt, config)


# ─────────────────────────────────────────────────────────────
# AI REP ASSISTANT — For Class Representative
# ─────────────────────────────────────────────────────────────
class AIRepAssistant:

    def draft_announcement(self, rough_idea: str, priority: str = "Normal") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Help a Class Rep draft a professional announcement.\n"
            f"Priority: {priority}\nIdea: \"{rough_idea}\"\n\n"
            f"Write a complete, formal announcement ready to post. "
            f"Return ONLY plain text. NO HTML tags. NO formatting. Just plain text."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5, max_output_tokens=1000
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def suggest_reply(self, student_name: str, student_message: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"A Class Rep needs to reply to:\n"
            f"Student: {student_name}\nMessage: \"{student_message}\"\n\n"
            f"Write a professional, empathetic reply (3-5 sentences). "
            f"Return ONLY plain text. NO HTML tags. NO formatting. NO bold. NO italics. "
            f"Just plain text with proper punctuation."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5, max_output_tokens=500
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def summarize_feedback(self, feedback_list: list) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if not feedback_list:
            return "📭 No feedback messages to summarize."
        messages_text = ""
        for i, fb in enumerate(feedback_list[:20], 1):
            if isinstance(fb, list) and len(fb) >= 5:
                messages_text += f"{i}. [{fb[2]}]: {fb[4]}\n"
        prompt = (
            f"Analyze these student feedback messages and provide a structured summary.\n\n"
            f"Messages:\n{messages_text}\n\n"
            f"## 📊 Feedback Summary\n"
            f"### Common Issues\n### Urgent Matters\n### General Sentiment\n### Recommended Actions\n"
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=1500
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def format_timetable(self, raw_timetable: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Format this raw timetable into a clean, structured announcement.\n\n"
            f"Raw:\n{raw_timetable}\n\n"
            f"Format: Day | Time | Course | Venue. Easy to read on mobile. "
            f"Return plain text only. NO HTML."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.2, max_output_tokens=1500
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def check_timetable_conflicts(self, raw_timetable: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Check this timetable for: time clashes, venue conflicts, back-to-back classes, "
            f"unusual hours, missing info.\n\nTimetable:\n{raw_timetable}\n\n"
            f"## 🔍 Conflict Report\nList each issue. If none, confirm it looks clean."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.2, max_output_tokens=1000
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def answer_timetable_question(self, question: str, timetable_text: str) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Timetable:\n{timetable_text}\n\n"
            f"Student question: {question}\n\n"
            f"Answer directly from the timetable. If not found, say so politely. Plain text only."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=500
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def analyze_feedback_inbox(self, feedback_list: list, announcements: list, timetable: list) -> dict:
        """
        Full inbox analysis — categorize, prioritize, auto-draft replies,
        detect deadlines, suggest announcements, summarize sentiment.
        Returns a structured dict the UI can render directly.
        """
        if not feedback_list:
            return {"error": "No feedback to analyze."}

        fb_text = ""
        for i, fb in enumerate(feedback_list[:30], 1):
            if isinstance(fb, list) and len(fb) >= 5:
                fb_text += f"{i}. [{fb[3]}] {fb[2]}: {fb[4]}\n"

        ann_text = ""
        for ann in announcements[:10]:
            if isinstance(ann, dict):
                ann_text += f"- [{ann.get('priority','')}] {ann.get('timestamp','')} — {ann.get('text','')}\n"

        tt_text = ""
        for entry in timetable[:20]:
            if isinstance(entry, dict):
                tt_text += f"- {entry.get('day','')} {entry.get('time','')} | {entry.get('course','')} | {entry.get('lecturer','')}\n"

        prompt = f"""You are an AI Class Manager analyzing a university class representative's inbox.

STUDENT FEEDBACK MESSAGES:
{fb_text}

CURRENT ANNOUNCEMENTS:
{ann_text if ann_text else "None"}

CLASS TIMETABLE:
{tt_text if tt_text else "None"}

Analyze everything and return a JSON object with this exact structure:
{{
  "summary": "2-3 sentence overall summary of the class situation",
  "sentiment": "Positive / Neutral / Stressed / Concerned",
  "sentiment_reason": "one sentence explaining why",
  "categories": {{
    "questions": ["list of messages that are simple questions"],
    "complaints": ["list of complaints needing rep attention"],
    "requests": ["list of requests or suggestions"],
    "urgent": ["list of urgent matters"]
  }},
  "auto_replies": [
    {{
      "student_name": "name",
      "original_message": "their message",
      "suggested_reply": "professional reply text (plain text, no HTML)",
      "confidence": "High/Medium/Low",
      "can_auto_send": true
    }}
  ],
  "suggested_announcements": [
    {{
      "text": "announcement text",
      "priority": "Normal or Urgent",
      "reason": "why this announcement is needed"
    }}
  ],
  "deadlines_detected": [
    {{
      "item": "what the deadline is for",
      "date": "date if mentioned",
      "reminder_draft": "reminder announcement text"
    }}
  ],
  "rep_action_items": ["list of things only the rep can handle personally"],
  "group_suggestion": "any group allocation recommendation based on feedback patterns"
}}

Return ONLY valid JSON. No markdown. No explanation."""

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=6000
        )
        try:
            result = _call_with_retry(REP_MODEL, prompt, config)
            import json as _json
            clean = result.strip().replace("```json", "").replace("```", "")
            return _json.loads(clean)
        except Exception as e:
            return {"error": f"Analysis failed: {str(e)}"}

    def generate_timetable_suggestion(
        self, courses: list, constraints: str = ""
    ) -> str:
        """Generate a full weekly timetable suggestion from a list of courses."""
        courses_text = "\n".join([f"- {c}" for c in courses])
        prompt = (
            f"Generate a balanced weekly university timetable for these courses:\n{courses_text}\n\n"
            f"Constraints: {constraints if constraints else 'None'}\n\n"
            f"Rules:\n"
            f"- Monday to Friday only\n"
            f"- Lectures between 8:00 AM and 6:00 PM\n"
            f"- No more than 3 consecutive hours without a break\n"
            f"- Spread courses evenly across the week\n"
            f"- Include day, time, course for each slot\n\n"
            f"Format as a clean table: Day | Time | Course\n"
            f"Then list any scheduling notes below. Plain text only, no HTML."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=3000
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def suggest_deadline_reminders(self, announcements: list) -> str:
        """Scan announcements for deadlines and draft reminder messages."""
        if not announcements:
            return "No announcements to scan."
        ann_text = ""
        for ann in announcements:
            if isinstance(ann, dict):
                ann_text += f"- [{ann.get('timestamp','')}] {ann.get('text','')}\n"
        prompt = (
            f"Scan these class announcements for any deadlines, submission dates, "
            f"exam dates, or time-sensitive events:\n\n{ann_text}\n\n"
            f"For each deadline found:\n"
            f"1. Extract the deadline item and date\n"
            f"2. Draft a reminder announcement for 3 days before\n"
            f"3. Draft a reminder announcement for 1 day before\n\n"
            f"If no deadlines found, say so clearly.\n"
            f"Format each reminder ready to post. Plain text only, no HTML."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=3000
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def suggest_group_allocation(self, df_roster, instructions: str = "") -> str:
        """Recommend group allocation strategy based on class composition."""
        if df_roster is None or df_roster.empty:
            return "No roster data available."
        try:
            import pandas as _pd
            summary = f"Total students: {len(df_roster)}\n"
            if "Course Code" in df_roster.columns:
                summary += f"Course breakdown:\n{df_roster['Course Code'].value_counts().to_string()}\n"
            if "Assigned Group" in df_roster.columns:
                current = df_roster['Assigned Group'].value_counts()
                summary += f"Current groups:\n{current.to_string()}\n"
        except:
            summary = f"Total students: {len(df_roster)}"

        prompt = (
            f"As a Class Rep AI assistant, recommend a group allocation strategy.\n\n"
            f"Class composition:\n{summary}\n\n"
            f"Special instructions: {instructions if instructions else 'None'}\n\n"
            f"Provide:\n"
            f"1. Recommended number of groups and size\n"
            f"2. Allocation strategy (how to mix students)\n"
            f"3. Any specific recommendations based on the class composition\n"
            f"4. Suggested group names\n"
            f"Be specific and practical. Plain text only, no HTML."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=2000
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def create_course_unit_groups(self, instruction: str, course_units: list, student_list: list) -> dict:
        """
        Parse rep instruction to create course-unit-specific groups.
        Example instruction: "Create groups for Thermodynamics, Mathematics, and Physics. 
                            3-4 students per group, mix by performance level."
        Returns: {
            "Thermodynamics": {"Group A": [students], "Group B": [students], ...},
            "Mathematics": {...},
            ...
        }
        """
        if not _key_manager.has_keys():
            return {"error": "No API keys found"}
        
        students_summary = f"Available students: {len(student_list)}\nCourse units: {', '.join(course_units)}"
        
        prompt = (
            f"Parse this class rep instruction to create balanced course-unit groups.\n\n"
            f"Instruction: \"{instruction}\"\n\n"
            f"{students_summary}\n"
            f"Student list: {', '.join(student_list[:20])}" + 
            (" ..." if len(student_list) > 20 else "") + "\n\n"
            f"Create groups for each course unit. Return JSON format:\n"
            f'{{"Thermodynamics": {{"Group A": ["Student1", "Student2", ...], "Group B": [...]}},\n'
            f'"Mathematics": {{...}}, ...}}\n\n'
            f"Balance groups by:\n"
            f"- Similar size (within 1 student)\n"
            f"- Mixed expertise levels if possible\n"
            f"- Ensure every student appears in every course unit group\n"
            f"Return ONLY valid JSON, no markdown, no explanation."
        )
        config = types.GenerateContentConfig(
            system_instruction=REP_SYSTEM_PROMPT,
            temperature=0.5, max_output_tokens=3000
        )
        result_str = _call_with_retry(REP_MODEL, prompt, config)
        
        try:
            # Try to parse as JSON
            import json
            result = json.loads(result_str)
            return {"status": "success", "groups": result}
        except json.JSONDecodeError:
            return {"status": "error", "message": "Could not parse groups. Please try with clearer instructions.", "raw": result_str}


# ─────────────────────────────────────────────────────────────
# AI ADMIN ASSISTANT — For Super Admin
# ─────────────────────────────────────────────────────────────
class AIAdminAssistant:
    """AI assistant for the Super Admin dashboard."""

    def summarize_all_feedback(self, feedback_list: list, dept: str = "ALL") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if not feedback_list:
            return "📭 No feedback to summarize."

        scope = f"department {dept}" if dept != "ALL" else "all departments"
        messages_text = ""
        for i, fb in enumerate(feedback_list[:30], 1):
            if isinstance(fb, list) and len(fb) >= 5:
                messages_text += f"{i}. [{fb[2]} | {fb[3] if len(fb)>5 else ''}]: {fb[4]}\n"

        prompt = (
            f"As a university admin, analyze feedback from {scope}.\n\n"
            f"Messages:\n{messages_text}\n\n"
            f"## 📊 University-Wide Feedback Analysis\n"
            f"### Top Issues Across Departments\n"
            f"### Departments Needing Attention\n"
            f"### Overall Student Sentiment\n"
            f"### Recommended Admin Actions\n"
        )
        config = types.GenerateContentConfig(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=2000
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def generate_broadcast(self, rough_idea: str, priority: str = "Normal") -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        prompt = (
            f"Draft a university-wide broadcast announcement.\n"
            f"Priority: {priority}\nIdea: \"{rough_idea}\"\n\n"
            f"This will go to ALL departments and year groups. "
            f"Make it formal, clear, and appropriately scoped. "
            f"Return plain text only. NO HTML."
        )
        config = types.GenerateContentConfig(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            temperature=0.4, max_output_tokens=800
        )
        return _call_with_retry(REP_MODEL, prompt, config)

    def analyze_enrollment(self, df: pd.DataFrame) -> str:
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."
        if df.empty:
            return "No enrollment data available."

        df = df.copy()
        df.columns = [c.strip() for c in df.columns]
        col_map = {}
        for c in df.columns:
            if c.lower() in ("department", "dept", "dep"):
                col_map[c] = "Department"
            elif c.lower() in ("year", "year_group", "year of study"):
                col_map[c] = "Year"
        df = df.rename(columns=col_map)

        if "Department" not in df.columns:
            df["Department"] = "Unknown"
        if "Year" not in df.columns:
            df["Year"] = "Unknown"

        summary = df.groupby(["Department", "Year"]).size().reset_index(name="Count")
        summary_text = summary.to_string(index=False)

        prompt = (
            f"Analyze this university enrollment data and provide insights.\n\n"
            f"Enrollment by Department and Year:\n{summary_text}\n\n"
            f"Provide:\n"
            f"1. Which dept/year has the most students\n"
            f"2. Which has the least (may need attention)\n"
            f"3. Overall enrollment health\n"
            f"4. Any notable patterns\n"
            f"Keep it concise and actionable for an admin. Plain text only."
        )
        config = types.GenerateContentConfig(
            system_instruction=ADMIN_SYSTEM_PROMPT,
            temperature=0.3, max_output_tokens=800
        )
        return _call_with_retry(REP_MODEL, prompt, config)

# ─────────────────────────────────────────────────────────────
# MASTER AI MEMORY SYSTEM — Layer 6
# ─────────────────────────────────────────────────────────────
class MasterAIMemorySystem:
    """
    Persistent memory for the Master Super Admin AI.
    Stores conversation summaries, preferences, and decisions
    across sessions in Google Sheets.
    
    Memory Types:
    - preference  : Alia's preferences and working style
    - decision    : Important decisions made about the portal
    - conversation: Summaries of past conversations
    - insight     : AI-generated insights about the portal
    """

    MEMORY_TYPES = ["preference", "decision", "conversation", "insight"]

    def __init__(self, db=None):
        self.db = db

    def save(self, mem_type: str, key: str, value: str) -> bool:
        if not self.db:
            return False
        try:
            return self.db.save_master_ai_memory(mem_type, key, value)
        except Exception as e:
            print(f"[Memory] Save error: {e}")
            return False

    def load_all(self) -> list:
        if not self.db:
            return []
        try:
            return self.db.load_master_ai_memory()
        except Exception as e:
            print(f"[Memory] Load error: {e}")
            return []

    def load_type(self, mem_type: str) -> list:
        if not self.db:
            return []
        try:
            return self.db.load_master_ai_memory(mem_type)
        except Exception as e:
            print(f"[Memory] Load type error: {e}")
            return []

    def build_memory_context(self) -> str:
        """Build a memory context block to inject into AI prompts."""
        all_memories = self.load_all()
        if not all_memories:
            return ""

        context = "=== ALIA'S MEMORY & PREFERENCES ===\n"

        # Group by type
        by_type = {}
        for mem in all_memories:
            t = mem.get("type", "other")
            by_type.setdefault(t, []).append(mem)

        if "preference" in by_type:
            context += "\n📌 PREFERENCES:\n"
            for m in by_type["preference"]:
                context += f"  • {m['key']}: {m['value']}\n"

        if "decision" in by_type:
            context += "\n🔑 PAST DECISIONS:\n"
            for m in by_type["decision"][-5:]:  # Last 5 decisions
                context += f"  • [{m.get('timestamp','')[:10]}] {m['key']}: {m['value']}\n"

        if "conversation" in by_type:
            context += "\n💬 RECENT CONVERSATION SUMMARIES:\n"
            for m in by_type["conversation"][-3:]:  # Last 3 summaries
                context += f"  • [{m.get('timestamp','')[:10]}] {m['value']}\n"

        if "insight" in by_type:
            context += "\n💡 PORTAL INSIGHTS:\n"
            for m in by_type["insight"][-3:]:
                context += f"  • {m['key']}: {m['value']}\n"

        context += "=== END MEMORY ===\n"
        return context

    def extract_and_save_memories(
        self,
        conversation: list,
        db=None
    ) -> dict:
        """
        After a conversation, use AI to extract memorable information
        and save it to persistent memory.
        """
        if not conversation or len(conversation) < 2:
            return {"saved": 0}

        if db:
            self.db = db

        # Build conversation text
        conv_text = ""
        for turn in conversation[-20:]:  # Last 20 messages
            role = "Alia" if turn["role"] == "user" else "AI"
            conv_text += f"{role}: {turn['content'][:200]}\n"

        prompt = (
            f"Analyze this conversation between Alia (Super Admin) and the Master AI:\n\n"
            f"{conv_text}\n\n"
            f"Extract memorable information and return a JSON object:\n"
            f"{{\n"
            f'  "preferences": [{{"key": "preference name", "value": "what Alia prefers"}}],\n'
            f'  "decisions": [{{"key": "decision topic", "value": "what was decided"}}],\n'
            f'  "summary": "2 sentence summary of this conversation",\n'
            f'  "insights": [{{"key": "insight topic", "value": "what was learned about the portal"}}]\n'
            f"}}\n\n"
            f"Only extract things worth remembering long-term.\n"
            f"If nothing is worth remembering, return empty arrays.\n"
            f"Return ONLY valid JSON. No markdown."
        )

        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            temperature=0.3,
            max_output_tokens=1000
        )

        try:
            result = _call_with_retry("models/gemini-2.5-flash", prompt, config)
            clean  = result.strip().replace("```json","").replace("```","")
            data   = json.loads(clean)

            saved_count = 0

            # Save preferences
            for pref in data.get("preferences", []):
                if pref.get("key") and pref.get("value"):
                    self.save("preference", pref["key"], pref["value"])
                    saved_count += 1

            # Save decisions
            for dec in data.get("decisions", []):
                if dec.get("key") and dec.get("value"):
                    self.save("decision", dec["key"], dec["value"])
                    saved_count += 1

            # Save conversation summary
            summary = data.get("summary", "")
            if summary:
                from datetime import datetime
                self.save(
                    "conversation",
                    f"session_{datetime.now().strftime('%Y%m%d_%H%M')}",
                    summary
                )
                saved_count += 1

            # Save insights
            for ins in data.get("insights", []):
                if ins.get("key") and ins.get("value"):
                    self.save("insight", ins["key"], ins["value"])
                    saved_count += 1

            return {"saved": saved_count, "data": data}

        except Exception as e:
            print(f"[Memory] Extract error: {e}")
            return {"saved": 0, "error": str(e)}
        
        # ─────────────────────────────────────────────────────────────
# MASTER AI MONITOR — Layer 7: Background Monitoring
# ─────────────────────────────────────────────────────────────
class MasterAIMonitor:
    """
    Background monitor for the Smart University Portal.
    Watches portal health, student activity, and AI engine status.
    Sends proactive Telegram/System alerts to Alia.
    """

    def __init__(self, db=None):
        self.db    = db
        self.model = "models/gemini-2.5-flash"

    def _send_whatsapp(self, message: str) -> dict:
        return {"status": "disabled", "message": "WhatsApp notifications disabled"}

    def _send_telegram(self, message: str) -> dict:
        """Send Telegram notification to Alia."""
        try:
            bot_token = st.secrets.get("ADMIN_TELEGRAM_TOKEN",  "")
            chat_id   = st.secrets.get("ADMIN_TELEGRAM_CHAT_ID","")
            if not bot_token or not chat_id:
                return {"error": "❌ ADMIN_TELEGRAM_TOKEN or ADMIN_TELEGRAM_CHAT_ID not set"}
            url  = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id"   : chat_id,
                "text"      : message,
                "parse_mode": "Markdown"
            }, timeout=10)
            if resp.status_code == 200:
                return {"status": "success", "channel": "telegram"}
            return {"error": f"Telegram API error: {resp.status_code}"}
        except Exception as e:
            return {"error": str(e)}

    def send_alert(self, message: str, channel: str = "both") -> dict:
        """
        Send alert to Alia via WhatsApp, Telegram, or both.
        channel: 'whatsapp' | 'telegram' | 'both'
        """
        results = {}
        if channel in ("whatsapp", "both"):
            results["whatsapp"] = self._send_whatsapp(message)
        if channel in ("telegram", "both"):
            results["telegram"] = self._send_telegram(message)
        return results

    def check_portal_health(
        self,
        df_all=None,
        reps_list=None,
        all_feedback=None,
        all_anns=None
    ) -> dict:
        """
        Run a full portal health check.
        Returns a structured report with issues and alerts.
        """
        issues   = []
        warnings = []
        healthy  = []

        # ── Check AI keys ─────────────────────────────────────
        key_count = _key_manager.total_keys()
        if key_count == 0:
            issues.append("🔴 No Gemini API keys configured — AI is down")
        elif key_count == 1:
            warnings.append("🟡 Only 1 Gemini key — consider adding more for redundancy")
        else:
            healthy.append(f"🟢 {key_count} Gemini keys active")

        # ── Check student data ────────────────────────────────
        student_count = len(df_all) if df_all is not None and not df_all.empty else 0
        if student_count == 0:
            warnings.append("🟡 No students registered yet")
        else:
            healthy.append(f"🟢 {student_count} students registered")

        # ── Check rep coverage ────────────────────────────────
        rep_count = len(reps_list) if reps_list else 0
        if rep_count == 0:
            warnings.append("🟡 No class rep accounts created")
        else:
            healthy.append(f"🟢 {rep_count} class rep account(s) active")

        # ── Check unreviewed feedback ─────────────────────────
        if all_feedback:
            unreviewed = [
                f for f in all_feedback
                if isinstance(f, list) and len(f) >= 4
                and str(f[3]).lower() == "pending"
            ]
            if len(unreviewed) > 5:
                warnings.append(
                    f"🟡 {len(unreviewed)} unreviewed feedback messages — students waiting"
                )
            elif unreviewed:
                warnings.append(f"🟡 {len(unreviewed)} pending feedback message(s)")
            else:
                healthy.append("🟢 All feedback reviewed")

        # ── Overall status ────────────────────────────────────
        if issues:
            overall = "🔴 Critical Issues Detected"
        elif warnings:
            overall = "🟡 Warnings — Attention Needed"
        else:
            overall = "🟢 All Systems Healthy"

        return {
            "overall" : overall,
            "issues"  : issues,
            "warnings": warnings,
            "healthy" : healthy,
            "counts"  : {
                "students" : student_count,
                "reps"     : rep_count,
                "feedback" : len(all_feedback) if all_feedback else 0,
                "ai_keys"  : key_count
            }
        }

    def generate_daily_report(
        self,
        df_all=None,
        reps_list=None,
        all_feedback=None,
        all_anns=None
    ) -> str:
        """
        Generate a daily summary report for Alia.
        Returns formatted text ready to send via WhatsApp/Telegram.
        """
        health = self.check_portal_health(
            df_all, reps_list, all_feedback, all_anns
        )

        from datetime import datetime
        today = datetime.now().strftime("%A, %d %B %Y")

        report = (
            f"🎓 *Smart University Portal*\n"
            f"📅 Daily Report — {today}\n\n"
            f"*Status:* {health['overall']}\n\n"
        )

        if health["issues"]:
            report += "*🔴 Critical Issues:*\n"
            for issue in health["issues"]:
                report += f"  {issue}\n"
            report += "\n"

        if health["warnings"]:
            report += "*🟡 Warnings:*\n"
            for w in health["warnings"]:
                report += f"  {w}\n"
            report += "\n"

        counts = health["counts"]
        report += (
            f"*📊 Quick Stats:*\n"
            f"  • Students: {counts['students']}\n"
            f"  • Class Reps: {counts['reps']}\n"
            f"  • Feedback: {counts['feedback']}\n"
            f"  • AI Keys: {counts['ai_keys']}\n\n"
        )

        if all_anns:
            recent_anns = [
                a for a in all_anns
                if isinstance(a, dict)
            ][:3]
            if recent_anns:
                report += "*📢 Recent Announcements:*\n"
                for ann in recent_anns:
                    report += f"  • {ann.get('text','')[:60]}...\n"
                report += "\n"

        report += "— Master AI 🤖"
        return report

    def ai_generate_alert(
        self,
        event_type: str,
        event_data: dict
    ) -> str:
        """
        Use AI to generate a smart, context-aware alert message.
        """
        prompt = (
            f"Generate a short WhatsApp alert for Alia, Super Admin of Smart University Portal.\n\n"
            f"Event type: {event_type}\n"
            f"Event data: {json.dumps(event_data)}\n\n"
            f"Rules:\n"
            f"- Maximum 3 sentences\n"
            f"- Start with an emoji\n"
            f"- Be direct and actionable\n"
            f"- Sign off as 'Master AI'\n"
            f"- Plain text only, no markdown except *bold* for key info"
        )
        config = types.GenerateContentConfig(
            system_instruction=MASTER_AI_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=200
        )
        return _call_with_retry(self.model, prompt, config)

# ─────────────────────────────────────────────────────────────
# GAS EDITOR — Read and write Google Apps Script code
# ─────────────────────────────────────────────────────────────
class GASEditor:
    """
    Reads and writes Google Apps Script code via Apps Script API.
    Uses service account credentials for authentication.
    """

    def __init__(self):
        self.script_id = None
        self.service   = None
        self._init_service()

    def _init_service(self):
        """Initialize the Apps Script API service."""
        try:
            import json as _json
            from google.oauth2 import service_account
            from googleapiclient.discovery import build

            # Load service account credentials
            sa_info    = _json.loads(st.secrets.get("GOOGLE_SERVICE_ACCOUNT", "{}"))
            self.script_id = st.secrets.get("APPS_SCRIPT_ID", "")

            if not sa_info or not self.script_id:
                print("[GASEditor] Missing credentials in secrets.toml")
                return

            credentials = service_account.Credentials.from_service_account_info(
                sa_info,
                scopes=[
                    "https://www.googleapis.com/auth/script.projects",
                    "https://www.googleapis.com/auth/script.deployments",
                    "https://www.googleapis.com/auth/drive",
                ]
            )
            self.service = build("script", "v1", credentials=credentials)
            print("[GASEditor] Apps Script API initialized successfully")

        except Exception as e:
            print(f"[GASEditor] Init error: {e}")
            self.service = None

    def is_ready(self) -> bool:
        return self.service is not None and bool(self.script_id)

    def read_all_files(self) -> dict:
        """
        Read all files in the Apps Script project.
        Returns dict of {filename: source_code}
        """
        if not self.is_ready():
            return {"error": "❌ GAS Editor not initialized. Check credentials."}
        try:
            response = self.service.projects().getContent(
                scriptId=self.script_id
            ).execute()

            files = {}
            for f in response.get("files", []):
                name   = f.get("name", "")
                source = f.get("source", "")
                ftype  = f.get("type", "")
                if ftype == "SERVER_JS":
                    files[f"{name}.gs"] = source
                elif ftype == "JSON":
                    files[f"{name}.json"] = source
                else:
                    files[name] = source

            return files

        except Exception as e:
            return {"error": f"❌ Could not read GAS files: {str(e)}"}

    def read_file(self, filename: str) -> str:
        """Read a specific GAS file by name."""
        files = self.read_all_files()
        if "error" in files:
            return files["error"]

        # Try with and without extension
        clean = filename.replace(".gs","").replace(".js","")
        for key, content in files.items():
            if key.replace(".gs","").replace(".js","").lower() == clean.lower():
                return content

        available = ", ".join(files.keys())
        return f"❌ File '{filename}' not found. Available: {available}"

    def write_file(self, filename: str, new_source: str) -> dict:
        """
        Write updated source code to a specific GAS file.
        Preserves all other files unchanged.
        """
        if not self.is_ready():
            return {"error": "❌ GAS Editor not initialized."}

        try:
            # Read current project content
            response = self.service.projects().getContent(
                scriptId=self.script_id
            ).execute()

            files      = response.get("files", [])
            clean_name = filename.replace(".gs","").replace(".js","")

            # Find and update the target file
            updated    = False
            new_files  = []
            for f in files:
                if f.get("name","").lower() == clean_name.lower():
                    f["source"] = new_source
                    updated     = True
                new_files.append(f)

            # If file doesn't exist, create it
            if not updated:
                new_files.append({
                    "name"  : clean_name,
                    "type"  : "SERVER_JS",
                    "source": new_source
                })

            # Push updated content back
            self.service.projects().updateContent(
                scriptId=self.script_id,
                body={"files": new_files}
            ).execute()

            return {
                "status" : "success",
                "message": f"✅ {filename} updated in Apps Script successfully!",
                "action" : "updated" if updated else "created"
            }

        except Exception as e:
            return {"error": f"❌ Could not write to GAS: {str(e)}"}

    def get_file_list(self) -> list:
        """Get list of all files in the project."""
        files = self.read_all_files()
        if "error" in files:
            return []
        return list(files.keys())


# ─────────────────────────────────────────────────────────────
# MASTER SUPER ADMIN AI — Layer 1: Chat Interface
# ─────────────────────────────────────────────────────────────
MASTER_AI_SYSTEM_PROMPT = """
You are the Master Super Admin AI for a university portal called "Smart University App" — 
a class management portal for Makerere University's College of Engineering, Design, Art and Technology.

The Super Admin's name is Alia. Always address her by name.

YOUR STRICT RULES:
1. You NEVER pretend to deploy, execute, or perform actions you haven't actually done.
2. You NEVER say "I am working on it", "I have deployed", "I am making changes" unless a real function was called and returned success.
3. You ONLY report actions that actually happened via real function calls in the backend.
4. When you write code, you present it and WAIT for Alia's approval — you never auto-deploy.
5. You are honest about what you can and cannot do.
6. You NEVER roleplay or simulate actions. Real actions only.
7. Do NOT narrate your plan before acting. When asked to write code, write it immediately and confirm with the result — no "I will now analyze...", no "Please give me a moment...". Act first, report after.
8. Never say "I am reading files", "I will analyze", "Please allow me a moment" — just do it and show the output.

YOUR CURRENT ACTIVE CAPABILITIES:
- Answer questions about the portal and its data
- Query real student, rep, feedback and announcement data
- Read and analyze the actual codebase files
- Suggest specific improvements based on real code
- Write code changes and present them for approval
- Save changes locally for testing
- Deploy approved changes to GitHub

Always respond in a structured, clear way. Use emojis where appropriate.
Be intelligent and proactive — but always honest and grounded in reality.
"""


class MasterSuperAdminAI:
    """
    The Master Super Admin AI — brain of the entire portal.
    Layer 1: Conversational chat interface with portal context awareness.
    """

    def __init__(self):
        self.model      = "models/gemini-2.5-flash"
        self.memory     = MasterAIMemorySystem()
        self.gas_editor = GASEditor()

    def write_gas_change(
        self,
        request: str,
        target_file: str = None
    ) -> dict:
        """
        Read GAS file, write changes, validate and return for approval.
        """
        if not self.gas_editor.is_ready():
            return {"error": "❌ GAS Editor not ready. Check GOOGLE_SERVICE_ACCOUNT and APPS_SCRIPT_ID in secrets.toml"}

        # Get available files
        available_files = self.gas_editor.get_file_list()
        if not available_files:
            return {"error": "❌ Could not read Apps Script project files."}

        # Detect target file
        if not target_file:
            # Try to find most relevant file from request
            request_lower = request.lower()
            for fname in available_files:
                clean = fname.lower().replace(".gs","")
                if clean in request_lower or any(
                    w in request_lower for w in clean.split()
                ):
                    target_file = fname
                    break

        # Default to Code.gs if nothing detected
        if not target_file:
            target_file = next(
                (f for f in available_files if "code" in f.lower()),
                available_files[0] if available_files else "Code.gs"
            )

        # Read current GAS code
        original_code = self.gas_editor.read_file(target_file)
        if original_code.startswith("❌"):
            return {"error": original_code}

        # Ask AI to write the change
        files_list = "\n".join([f"  - {f}" for f in available_files])
        prompt = (
            f"You are editing a Google Apps Script file for a university portal.\n\n"
            f"Available files in the project:\n{files_list}\n\n"
            f"Target file: {target_file}\n\n"
            f"=== CURRENT CODE ===\n"
            f"{original_code[:4000]}\n"
            f"=== END CODE ===\n\n"
            f"Alia's request: \"{request}\"\n\n"
            f"Rules:\n"
            f"- Write the COMPLETE updated file\n"
            f"- Keep ALL existing functions intact\n"
            f"- Only ADD or MODIFY what is needed\n"
            f"- Mark your changes with // [MASTER AI EDIT]\n"
            f"- Return ONLY raw JavaScript/GAS code\n"
            f"- No markdown. No backticks. No explanation.\n\n"
            f"Write the complete updated {target_file} now:"
        )

        config = types.GenerateContentConfig(
            system_instruction=MASTER_AI_SYSTEM_PROMPT,
            temperature=0.2,
            max_output_tokens=8000
        )

        new_code = _call_with_retry(self.model, prompt, config)

        # Clean up markdown if any
        new_code = new_code.strip()
        for strip in ["```javascript", "```js", "```"]:
            if new_code.startswith(strip):
                new_code = new_code[len(strip):]
        if new_code.endswith("```"):
            new_code = new_code[:-3]
        new_code = new_code.strip()

        # Basic validation
        issues = []
        orig_funcs = set(__import__('re').findall(r'function\s+(\w+)', original_code))
        new_funcs  = set(__import__('re').findall(r'function\s+(\w+)', new_code))
        missing    = orig_funcs - new_funcs
        if missing:
            issues.append(f"❌ Missing GAS functions: {', '.join(missing)}")

        orig_lines = len(original_code.splitlines())
        new_lines  = len(new_code.splitlines())
        if orig_lines > 20 and new_lines < orig_lines * 0.6:
            issues.append(f"⚠️ New code is {new_lines} lines vs original {orig_lines}")

        validation = {
            "valid"  : len(issues) == 0,
            "issues" : issues,
            "summary": "✅ Validation passed" if not issues else f"🚨 {len(issues)} issue(s) found"
        }

        return {
            "target_file"  : target_file,
            "original_code": original_code,
            "new_code"     : new_code,
            "request"      : request,
            "type"         : "gas",
            "status"       : "pending_approval",
            "validation"   : validation
        }

    def _build_portal_context(self, db=None, df_all=None, reps_list=None) -> str:
        """Build a rich context block about the current portal state."""
        context = "=== PORTAL CONTEXT ===\n"
        context += "Portal Name: Smart University App — Makerere University\n"
        context += "Stack: Streamlit + Google Apps Script + Google Sheets\n"
        context += f"AI Engine: Gemini 2.5 Flash with {_key_manager.total_keys()} key(s) loaded\n"

        if df_all is not None and not df_all.empty:
            context += f"Total Students Registered: {len(df_all)}\n"
            dept_col = next((c for c in ["Department", "department", "dept"] if c in df_all.columns), None)
            if dept_col:
                dept_counts = df_all[dept_col].value_counts().to_dict()
                context += f"Students per Department: {dept_counts}\n"

            # Full student roster — safe since student count is small
            context += "\n=== FULL STUDENT ROSTER ===\n"
            for _, row in df_all.iterrows():
                name = str(row.get("Student Name", row.get("student_name", "Unknown")))
                reg = str(row.get("Reg Number", row.get("reg_number", "")))
                dept = str(row.get("Department", row.get("department", "")))
                year = str(row.get("Year", row.get("year", "")))
                course = str(row.get("Course Code", row.get("course_code", "")))
                group = str(row.get("Assigned Group", row.get("group", "No group")))
                context += f"• {name} | Reg: {reg} | Dept: {dept} | Year: {year} | Course: {course} | Group: {group}\n"
            context += "=== END ROSTER ===\n"
        else:
            context += "Student Data: Not loaded\n"
        if reps_list:
            context += f"Class Rep Accounts: {len(reps_list)}\n"

        context += "=== END PORTAL CONTEXT ===\n"
        return context

    def _read_codebase(self, specific_file: str = None) -> str:
        """
        Read portal source files and return their contents as context.
        If specific_file is given, read only that file.
        Otherwise read all core files.
        """
        # Core files to read
        CORE_FILES = [
            "app.py",
            "ai_engine.py",
            "database.py",
            "config.py",
            "student.py",
            "class_rep.py",
            "Superadmin.py",
            "notifier.py",
            "image_generator.py",
            "utils/mobile.py",
        ]

        code_context = "=== PORTAL CODEBASE ===\n"

        files_to_read = [specific_file] if specific_file else CORE_FILES

        for filepath in files_to_read:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    content = f.read()
                # Limit each file to 3000 chars to avoid token overflow
                if len(content) > 1500:
                    content = content[:1500] + "\n... [truncated for context] ..."
                code_context += f"\n--- FILE: {filepath} ---\n{content}\n--- END: {filepath} ---\n"
            except FileNotFoundError:
                code_context += f"\n--- FILE: {filepath} --- NOT FOUND ---\n"
            except Exception as e:
                code_context += f"\n--- FILE: {filepath} --- ERROR: {str(e)} ---\n"

        code_context += "\n=== END CODEBASE ===\n"
        return code_context

    def _detect_code_file(self, message: str) -> str:
        """Detect if user is asking about a specific file."""
        message_lower = message.lower()
        file_map = {
            "notifier": "notifier.py",
            "notification": "notifier.py",
            "whatsapp": "notifier.py",
            "telegram": "notifier.py",
            "database": "database.py",
            "db": "database.py",
            "sheets": "database.py",
            "config": "config.py",
            "department": "config.py",
            "student": "student.py",
            "student portal": "student.py",
            "class rep": "class_rep.py",
            "rep dashboard": "class_rep.py",
            "superadmin": "Superadmin.py",
            "super admin": "Superadmin.py",
            "admin": "Superadmin.py",
            "image": "image_generator.py",
            "image generator": "image_generator.py",
            "app": "app.py",
            "entry point": "app.py",
            "main": "app.py",
            "mobile": "utils/mobile.py",
            "ai engine": "ai_engine.py",
            "ai": "ai_engine.py",
            "gemini": "ai_engine.py",
        }
        for keyword, filename in file_map.items():
            if keyword in message_lower:
                return filename
        return None

    def suggest_improvements(
        self,
        target: str = "full_portal",
        db=None,
        df_all=None,
        reps_list=None,
        all_feedback=None,
        all_anns=None
    ) -> str:
        """
        Analyze the portal codebase and data,
        then suggest specific, actionable improvements.
        target: 'full_portal' | filename like 'notifier.py'
        """
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."

        # Build contexts
        portal_context = self._build_portal_context(db, df_all, reps_list)

        # Read relevant code
        if target == "full_portal":
            code_context = self._read_codebase()
        else:
            code_context = self._read_codebase(target)

        # Build data context
        data_context = "=== PORTAL DATA SNAPSHOT ===\n"
        if df_all is not None and not df_all.empty:
            data_context += f"Students: {len(df_all)}\n"
        if reps_list:
            data_context += f"Class Reps: {len(reps_list)}\n"
        if all_feedback:
            data_context += f"Feedback Messages: {len(all_feedback)}\n"
        if all_anns:
            data_context += f"Announcements: {len(all_anns)}\n"
        data_context += "=== END DATA SNAPSHOT ===\n"

        prompt = (
            f"{portal_context}\n"
            f"{data_context}\n"
            f"{code_context}\n\n"
            f"You are analyzing the Smart University Portal codebase as a senior developer.\n\n"
            f"Provide a structured improvement report with these sections:\n\n"
            f"### 🔴 Critical Issues\n"
            f"List any bugs, security holes, or broken logic you detect in the actual code.\n\n"
            f"### 🟡 Performance Improvements\n"
            f"List specific functions or patterns that could be optimized.\n"
            f"Reference actual function names and file names.\n\n"
            f"### 🟢 Feature Suggestions\n"
            f"List 5 new features that would genuinely improve this portal.\n"
            f"Be specific — not generic advice.\n\n"
            f"### 🔵 Code Quality\n"
            f"List specific code quality improvements — naming, structure, duplication.\n\n"
            f"### ⭐ Top Priority\n"
            f"Pick the single most important improvement and explain exactly how to implement it.\n\n"
            f"Be specific but concise. Reference actual file names and function names. "
            f"For each point write maximum 2-3 sentences. "
            f"Do NOT over-explain. Alia is the developer — he understands code. "
            f"Make sure you COMPLETE every section fully before stopping."
        )

        config = types.GenerateContentConfig(
            system_instruction=MASTER_AI_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=8000
        )
        return _call_with_retry(self.model, prompt, config)

    def _find_section(self, file_content: str, request: str) -> tuple[int, int]:
        """
        Find the most relevant line range in a large file
        by matching request keywords against function/section names.
        Returns (start_line, end_line).
        """
        lines = file_content.splitlines()
        request_lower = request.lower()

        # Map common requests to anchor strings in student.py
        SECTION_ANCHORS = {
            "register": "show_reg_form",
            "registration": "show_reg_form",
            "email": "register_form",
            "login": "student_logged_in",
            "pin": "show_set_pin",
            "forgot": "show_forgot_pin",
            "announcement": "tab_notices",
            "notice": "tab_notices",
            "material": "tab_materials",
            "group": "tab_group",
            "message": "tab_message",
            "reply": "tab_replies",
            "timetable": "tab_timetable",
            "profile": "tab_profile",
            "notifications": "Class Notifications",
            "contact": "update_contact",
            "ai": "tab_ai",
            "chat": "ai_chat_form",
            "feature": "tab_features",
            "logout": "Log Out",
        }

        anchor = None
        for keyword, anchor_str in SECTION_ANCHORS.items():
            if keyword in request_lower:
                anchor = anchor_str
                break

        if anchor:
            for i, line in enumerate(lines):
                if anchor.lower() in line.lower():
                    start = max(0, i - 5)
                    end = min(len(lines), i + 400)
                    return start, end

        # Fallback: score-based search
        keywords = [w for w in request_lower.split()
                    if len(w) > 3 and w not in
                    ("add", "the", "and", "for", "with", "this", "that", "into", "from")]
        best_start = 0
        best_score = 0
        for i, line in enumerate(lines):
            score = sum(1 for kw in keywords if kw in line.lower())
            if score > best_score:
                best_score = score
                best_start = max(0, i - 10)

        return best_start, min(len(lines), best_start + 400)

    def analyze_specific_issue(
        self,
        issue: str,
        db=None,
        df_all=None,
        reps_list=None
    ) -> str:
        """
        Deep dive into a specific issue or area the admin mentions.
        """
        if not _key_manager.has_keys():
            return "⚠️ No API keys found."

        # Detect which file is most relevant
        specific_file = self._detect_code_file(issue)
        code_context = self._read_codebase(specific_file)
        portal_context = self._build_portal_context(db, df_all, reps_list)

        prompt = (
            f"{portal_context}\n"
            f"{code_context}\n\n"
            f"Alia is asking about a specific issue or area:\n"
            f"\"{issue}\"\n\n"
            f"Analyze the relevant code deeply and provide:\n\n"
            f"### 🔍 What I Found\n"
            f"Explain exactly what the current code does in this area.\n\n"
            f"### ⚠️ Problems Detected\n"
            f"List any issues, limitations, or risks you see.\n\n"
            f"### ✅ Recommended Fix\n"
            f"Give a specific, actionable recommendation.\n"
            f"If code needs to be changed, describe exactly what to change.\n\n"
            f"### 📈 Expected Improvement\n"
            f"Explain what will be better after the fix.\n\n"
            f"Be direct and technical. Alia is the developer."
        )

        config = types.GenerateContentConfig(
            system_instruction=MASTER_AI_SYSTEM_PROMPT,
            temperature=0.4,
            max_output_tokens=3000
        )
        return _call_with_retry(self.model, prompt, config)

    def write_code_change(
        self,
        request: str,
        target_file: str = None,
        db=None,
        df_all=None,
        reps_list=None
    ) -> dict:
        if not _key_manager.has_keys():
            return {"error": "⚠️ No API keys found."}

        if not target_file:
            target_file = self._detect_code_file(request)
        if not target_file:
            target_file = "app.py"

        try:
            with open(target_file, "r", encoding="utf-8") as f:
                original_code = f.read()
        except FileNotFoundError:
            original_code = "# New file"
        except Exception as e:
            return {"error": f"❌ Could not read {target_file}: {str(e)}"}

        portal_context = self._build_portal_context(db, df_all, reps_list)
        total_lines = len(original_code.splitlines())

        # ── LARGE FILE: Surgical insertion ────────────────────
        if total_lines > 500:
            lines = original_code.splitlines()
            keywords = [w for w in request.lower().split()
                        if len(w) > 3 and w not in
                        ("add", "the", "and", "for", "with", "this", "that", "into", "from")]
            best_start = 0
            best_score = 0

            for i, line in enumerate(lines):
                score = sum(1 for kw in keywords if kw in line.lower())
                if score > best_score:
                    best_score = score
                    best_start = max(0, i - 10)

            relevant_section = "\n".join(lines[best_start:best_start + 400])
            plan_prompt = (
                f"You are editing {target_file} which has {total_lines} lines.\n\n"
                f"Alia's request: \"{request}\"\n\n"
                f"Here is the most relevant section (lines {best_start+1} to {best_start+400}):\n\n"
                f"{relevant_section}\n\n"
                f"STRICT RULES FOR VALID PYTHON:\n"
                f"1. After every 'def function():' line, the NEXT line MUST be indented with 4 spaces.\n"
                f"2. All code inside functions MUST be indented exactly 4 spaces.\n"
                f"3. Class methods inside classes MUST be indented 4 spaces.\n"
                f"4. No empty indentation blocks - use 'pass' if nothing else.\n"
                f"5. Every 'if:', 'elif:', 'else:', 'for:', 'while:' MUST have an indented block after it.\n"
                f"6. WRITE VALID PYTHON SYNTAX - no trailing commas, no missing colons.\n"
                f"7. Before returning, verify: every colon is followed by an indented next line.\n\n"
                f"===SEARCH===\n"
                f"paste exactly one line from the section above\n"
                f"===CODE===\n"
                f"your new python code here, proper indentation\n"
                f"===EXPLANATION===\n"
                f"one sentence describing what was added\n"
            )

            config = types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4000
            )

            try:
                plan_result = _call_with_retry(self.model, plan_prompt, config)

                def _extract(text, start_tag, end_tag):
                    s = text.find(start_tag)
                    if s == -1:
                        return ""
                    s = s + len(start_tag)
                    if s < len(text) and text[s] == "\n":
                        s += 1
                    e = text.find(end_tag, s)
                    if e == -1:
                        return text[s:].strip()
                    return text[s:e].strip()

                search_string = _extract(plan_result, "===SEARCH===", "===CODE===")
                new_snippet = _extract(plan_result, "===CODE===", "===EXPLANATION===")
                explanation = _extract(plan_result, "===EXPLANATION===", "<<<END>>>") or "Surgical edit"

                # Strip any leaked delimiter lines
                new_snippet = "\n".join(
                    line for line in new_snippet.splitlines()
                    if not line.strip().startswith("===")
                )

                # Search string must be a single clean line
                search_string = search_string.splitlines()[0].strip() if search_string else ""

                # Validate snippet is not empty
                if not new_snippet.strip():
                    return {"error": "❌ AI returned an empty code block. Please be more specific in your request."}

                # ── Auto-fix snippet syntax ──
                def _fix_snippet_indentation(snippet):
                    """Auto-fix common indentation issues."""
                    lines = snippet.splitlines()
                    fixed = []
                    indent_level = 0

                    for i, line in enumerate(lines):
                        stripped = line.lstrip()

                        # Check if line is a block starter
                        if any(stripped.startswith(x) for x in ['def ', 'class ', 'if ', 'elif ', 'else:', 'for ', 'while ', 'try:', 'except ', 'finally:', 'with ']):
                            if stripped.endswith(':'):
                                if i + 1 < len(lines):
                                    next_line = lines[i + 1].lstrip()
                                    # If next line has no indentation or less than 4 spaces, fix it
                                    if next_line and not lines[i + 1].startswith(' ' * 4):
                                        lines[i + 1] = '    ' + lines[i + 1].lstrip()
                                fixed.append(line)
                                continue

                        # Ensure proper indentation for lines inside blocks
                        if i > 0 and lines[i-1].strip().endswith(':') and not line.startswith(' ' * 4):
                            if line.strip() and not line.strip().startswith('#'):
                                fixed.append('    ' + stripped)
                                continue

                        fixed.append(line)

                    return '\n'.join(fixed)

                def _check_snippet(snippet):
                    """Check if snippet is valid Python."""
                    try:
                        compile(snippet, "<snippet>", "exec")
                        return True, None
                    except SyntaxError as e:
                        return False, e

                # First, try to auto-fix indentation
                new_snippet = _fix_snippet_indentation(new_snippet)

                # Check syntax
                ok, err = _check_snippet(new_snippet)
                if not ok:
                    # Ask AI to fix the snippet
                    fix_prompt = (
                        f"This Python code snippet has a syntax error: {err.msg}\n"
                        f"Error on line {err.lineno}.\n\n"
                        f"Broken snippet:\n```python\n{new_snippet}\n```\n\n"
                        f"Fix the syntax error. Pay attention to indentation after colons.\n"
                        f"Return ONLY the corrected Python code. No markdown. No backticks. No explanation."
                    )
                    fix_config = types.GenerateContentConfig(
                        temperature=0.1,
                        max_output_tokens=2000
                    )
                    new_snippet = _call_with_retry(self.model, fix_prompt, fix_config)
                    new_snippet = new_snippet.strip()
                    # Clean markdown
                    for marker in ["```python", "```"]:
                        if new_snippet.startswith(marker):
                            new_snippet = new_snippet[len(marker):]
                        if new_snippet.endswith("```"):
                            new_snippet = new_snippet[:-3]
                    new_snippet = new_snippet.strip()

                    # Auto-fix again
                    new_snippet = _fix_snippet_indentation(new_snippet)

                    # Check again
                    ok, err = _check_snippet(new_snippet)
                    if not ok:
                        # One more attempt with more explicit prompt
                        fix_prompt_2 = (
                            f"Fix this Python syntax error: {err.msg} on line {err.lineno}\n\n"
                            f"```python\n{new_snippet}\n```\n\n"
                            f"CRITICAL: Add proper indentation after colons. Use 4 spaces.\n"
                            f"Return only the fixed Python code. No markdown."
                        )
                        new_snippet = _call_with_retry(self.model, fix_prompt_2, fix_config)
                        new_snippet = new_snippet.strip()
                        # Clean markdown
                        for marker in ["```python", "```"]:
                            if new_snippet.startswith(marker):
                                new_snippet = new_snippet[len(marker):]
                            if new_snippet.endswith("```"):
                                new_snippet = new_snippet[:-3]
                        new_snippet = new_snippet.strip()

                        ok, err = _check_snippet(new_snippet)
                        if not ok:
                            return {"error": f"❌ AI generated invalid Python after 2 attempts: {err.msg} on line {err.lineno}. Try rephrasing your request more specifically."}

                # Find the search line by index for precise insertion
                if search_string and search_string in original_code:
                    insert_after_idx = None
                    for i, line in enumerate(lines):
                        if search_string.strip() == line.strip():
                            insert_after_idx = i
                            indent = len(line) - len(line.lstrip())
                            indent_str = " " * indent
                            break

                    if insert_after_idx is None:
                        # fallback: partial match
                        for i, line in enumerate(lines):
                            if search_string.strip() in line.strip():
                                insert_after_idx = i
                                indent = len(line) - len(line.lstrip())
                                indent_str = " " * indent
                                break

                    if insert_after_idx is not None:
                        # Fix indentation of snippet to match insertion point
                        snippet_lines = new_snippet.splitlines()
                        fixed_lines = []
                        for sl in snippet_lines:
                            if sl.strip() == "":
                                fixed_lines.append("")
                            else:
                                fixed_lines.append(indent_str + sl.lstrip())
                        fixed_snippet = "\n".join(fixed_lines)

                        lines.insert(insert_after_idx + 1, fixed_snippet)
                        new_code = "\n".join(lines)
                    else:
                        new_code = original_code + "\n\n# [MASTER AI EDIT]\n" + new_snippet
                else:
                    new_code = original_code + "\n\n# [MASTER AI EDIT]\n" + new_snippet

            except Exception as e:
                return {"error": f"❌ Could not plan surgical edit: {str(e)}"}

        # ── SMALL FILE: Full rewrite ──────────────────────────
        else:
            prompt = (
                f"{portal_context}\n\n"
                f"=== CURRENT CODE OF {target_file} ===\n"
                f"{original_code}\n"
                f"=== END CURRENT CODE ===\n\n"
                f"Alia's request: \"{request}\"\n\n"
                f"You are a senior Python/Streamlit developer.\n"
                f"Write the complete updated version of {target_file}.\n\n"
                f"RULES FOR VALID PYTHON:\n"
                f"1. Every function/class/if/for/while MUST have proper 4-space indentation.\n"
                f"2. After every ':' the next line MUST be indented.\n"
                f"3. No empty indentation blocks - use 'pass' if needed.\n"
                f"4. Keep ALL existing functionality intact.\n"
                f"5. Mark your changes with # [MASTER AI EDIT]\n"
                f"6. Return ONLY raw Python code. No markdown. No backticks.\n\n"
                f"Write the complete updated {target_file} now:"
            )
            config = types.GenerateContentConfig(
                system_instruction=MASTER_AI_SYSTEM_PROMPT + "\nCRITICAL: Generate ONLY valid Python code with proper indentation. Every colon must be followed by an indented block.",
                temperature=0.2,
                max_output_tokens=8000
            )
            new_code = _call_with_retry(self.model, prompt, config)
            new_code = new_code.strip()
            for strip in ["```python", "```"]:
                if new_code.startswith(strip):
                    new_code = new_code[len(strip):]
            if new_code.endswith("```"):
                new_code = new_code[:-3]
            new_code = new_code.strip()
            explanation = "Full file rewrite"

        # ── Apply black formatter ──────────────────────────
        new_code = format_code_with_black(new_code)

        # ── Validate ──────────────────────────────────────────
        validation = self._validate_code_change(original_code, new_code, target_file)

        # If validation fails, try to auto-fix
        if not validation["valid"]:
            issues_text = "\n".join(validation["issues"])

            # Check if it's an indentation error
            if "indented block" in issues_text.lower():
                # Try to fix indentation automatically
                fixed_code = []
                lines = new_code.splitlines()
                for i, line in enumerate(lines):
                    stripped = line.lstrip()
                    # If line is a block starter and next line has no indent, fix it
                    if i > 0 and i < len(lines) - 1:
                        prev_line = lines[i-1].strip()
                        if prev_line.endswith(':') and not line.startswith(' ' * 4):
                            if stripped and not stripped.startswith('#'):
                                fixed_code.append('    ' + stripped)
                                continue
                    fixed_code.append(line)
                new_code = '\n'.join(fixed_code)
                new_code = format_code_with_black(new_code)
                validation = self._validate_code_change(original_code, new_code, target_file)

            # If still failing, try one more AI fix
            if not validation["valid"]:
                has_syntax = any("Syntax error" in i for i in validation["issues"])
                if has_syntax and total_lines <= 500:
                    issues_text = "\n".join(validation["issues"])
                    fix_prompt = (
                        f"Your generated code for {target_file} has this error:\n"
                        f"{issues_text}\n\n"
                        f"Original file (keep all functions and classes):\n{original_code}\n\n"
                        f"Fix the error. Pay special attention to indentation after colons.\n"
                        f"Return ONLY raw Python code, no markdown, no backticks."
                    )
                    config2 = types.GenerateContentConfig(
                        system_instruction=MASTER_AI_SYSTEM_PROMPT + "\nCRITICAL: Fix indentation errors. Every colon must have an indented block after it.",
                        temperature=0.1,
                        max_output_tokens=8000
                    )
                    new_code = _call_with_retry(self.model, fix_prompt, config2)
                    new_code = new_code.strip()
                    for strip in ["```python", "```"]:
                        if new_code.startswith(strip):
                            new_code = new_code[len(strip):]
                    if new_code.endswith("```"):
                        new_code = new_code[:-3]
                    new_code = new_code.strip()
                    new_code = format_code_with_black(new_code)
                    validation = self._validate_code_change(original_code, new_code, target_file)

        return {
            "target_file": target_file,
            "original_code": original_code,
            "new_code": new_code,
            "request": request,
            "explanation": explanation,
            "status": "pending_approval",
            "validation": validation
        }

    def save_locally(self, target_file: str, new_code: str) -> dict:
        """
        Save code change locally so Alia can test before deploying to GitHub.
        Streamlit will auto-reload the changes immediately.
        """
        import shutil
        from datetime import datetime

        # First create a backup of the original file
        try:
            backup_name = f"{target_file}.backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            shutil.copy2(target_file, backup_name)
            backup_created = True
        except Exception:
            backup_created = False

        # Write new code to the actual file
        try:
            # Format code before saving
            formatted_code = format_code_with_black(new_code)
            with open(target_file, "w", encoding="utf-8") as f:
                f.write(formatted_code)
            return {
                "status": "success",
                "message": f"✅ {target_file} saved locally!",
                "backup_created": backup_created,
                "backup_name": backup_name if backup_created else None
            }
        except Exception as e:
            return {"error": f"❌ Could not save locally: {str(e)}"}

    def _validate_code_change(self, original_code, new_code, target_file):
        import re

        issues = []

        # Syntax check first — if broken, stop here
        try:
            compile(new_code, target_file, "exec")
        except SyntaxError as e:
            return {
                "valid": False,
                "issues": [f"❌ Syntax error on line {e.lineno}: {e.msg}"],
                "summary": "🚨 Syntax error — fix before approving"
            }

        # Structural checks only if syntax is clean
        original_funcs = set(re.findall(r"^def\s+(\w+)", original_code, re.MULTILINE))
        original_classes = set(re.findall(r"^class\s+(\w+)", original_code, re.MULTILINE))
        new_funcs = set(re.findall(r"^def\s+(\w+)", new_code, re.MULTILINE))
        new_classes = set(re.findall(r"^class\s+(\w+)", new_code, re.MULTILINE))

        missing_funcs = original_funcs - new_funcs
        missing_classes = original_classes - new_classes

        if missing_funcs:
            issues.append(f"❌ Missing functions: {', '.join(missing_funcs)}")
        if missing_classes:
            issues.append(f"❌ Missing classes: {', '.join(missing_classes)}")

        original_lines = len(original_code.splitlines())
        new_lines = len(new_code.splitlines())
        if original_lines > 20 and new_lines < original_lines * 0.6:
            issues.append(f"⚠️ New code is {new_lines} lines vs original {original_lines} — suspiciously shorter")

        if issues:
            return {
                "valid": False,
                "issues": issues,
                "summary": f"🚨 Validation failed — {len(issues)} issue(s) found"
            }

        return {
            "valid": True,
            "issues": [],
            "summary": f"✅ Validation passed — all {len(original_funcs)} functions and {len(original_classes)} classes preserved",
            "funcs_preserved": len(original_funcs),
            "lines_original": original_lines,
            "lines_new": new_lines
        }

    def deploy_code_change(self, target_file: str, new_code: str) -> dict:
        """
        Deploy approved code change to GitHub.
        Streamlit Cloud auto-redeploys when GitHub updates.
        """
        import requests
        import base64

        token = st.secrets.get("GITHUB_TOKEN", "")
        repo = st.secrets.get("GITHUB_REPO", "")

        if not token or not repo:
            return {"error": "❌ GITHUB_TOKEN or GITHUB_REPO missing from secrets.toml"}

        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json"
        }

        # Get current file SHA — required by GitHub API to update a file
        url = f"https://api.github.com/repos/{repo}/contents/{target_file}"
        get_resp = requests.get(url, headers=headers)

        if get_resp.status_code == 200:
            sha = get_resp.json()["sha"]
        elif get_resp.status_code == 404:
            sha = None  # New file
        else:
            return {"error": f"❌ GitHub API error: {get_resp.status_code} — {get_resp.text}"}

        # Format code before deploying
        formatted_code = format_code_with_black(new_code)

        # Encode new code to base64
        encoded = base64.b64encode(formatted_code.encode("utf-8")).decode("utf-8")

        # Prepare commit payload
        payload = {
            "message": f"[Master AI] {target_file} — auto update",
            "content": encoded,
            "branch": "main"
        }
        if sha:
            payload["sha"] = sha

        # Push to GitHub
        put_resp = requests.put(url, headers=headers, json=payload)

        if put_resp.status_code in (200, 201):
            return {
                "status": "success",
                "message": f"✅ {target_file} pushed to GitHub successfully! Streamlit is redeploying...",
                "commit": put_resp.json().get("commit", {}).get("sha", "")[:7]
            }
        else:
            return {
                "error": f"❌ GitHub push failed: {put_resp.status_code} — {put_resp.text[:200]}"
            }

    def _detect_intent(self, message: str) -> str:
        """Detect what the user wants to do from their message."""
        message_lower = message.lower()

        if any(w in message_lower for w in ["how many students", "student count", "total students", "students registered"]):
            return "count_students"
        if any(w in message_lower for w in ["list students", "show students", "all students", "student list"]):
            return "list_students"
        if any(w in message_lower for w in ["list reps", "show reps", "rep accounts", "class reps"]):
            return "list_reps"
        if any(w in message_lower for w in ["feedback", "complaints", "messages from students"]):
            return "show_feedback"
        if any(w in message_lower for w in ["announcements", "broadcasts", "notices"]):
            return "show_announcements"
        if any(w in message_lower for w in ["departments", "list departments", "show departments"]):
            return "list_departments"
        if any(w in message_lower for w in ["status", "portal status", "health", "how is the portal"]):
            return "portal_status"
        if any(w in message_lower for w in ["sheets", "list sheets", "show sheets"]):
            return "list_sheets"
        if any(w in message_lower for w in [
            "add department", "create department", "new department",
            "add a department", "create a department"
        ]):
            return "add_department"

        if any(w in message_lower for w in [
            "assign rep", "assign a rep", "create rep", "add rep",
            "assign class rep", "create class rep", "add class rep",
            "new rep", "new class rep", "set rep"
        ]):
            return "assign_rep"

        if any(w in message_lower for w in [
            "delete department", "remove department", "drop department"
        ]):
            return "delete_department"

        if any(w in message_lower for w in [
            "delete rep", "remove rep", "delete class rep", "remove class rep"
        ]):
            return "delete_rep"

        if any(w in message_lower for w in [
            "reset rep password", "reset password", "change rep password"
        ]):
            return "reset_rep_password"

        if any(w in message_lower for w in [
            "broadcast", "send announcement to all",
            "announce to all", "broadcast announcement",
            "send broadcast", "post broadcast"
        ]):
            return "broadcast_announcement"

        if any(w in message_lower for w in [
            "post announcement", "send announcement", "add announcement",
            "create announcement", "new announcement"
        ]):
            return "post_announcement"

        if any(w in message_lower for w in [
            "delete announcement", "remove announcement"
        ]):
            return "delete_announcement"

        if any(w in message_lower for w in [
            "delete student", "remove student", "drop student"
        ]):
            return "delete_student"

        if any(w in message_lower for w in [
            "assign group", "assign student to group",
            "put student in group", "move student to group",
            "allocate group", "set group"
        ]):
            return "assign_group"

        if any(w in message_lower for w in [
            "add timetable", "post timetable", "create timetable",
            "add class", "schedule class", "add lecture"
        ]):
            return "post_timetable"

        if any(w in message_lower for w in [
            "delete timetable", "remove timetable",
            "remove class", "delete class", "remove lecture"
        ]):
            return "delete_timetable"

        if any(w in message_lower for w in [
            "notify class", "send notification",
            "message class", "notify students"
        ]):
            return "notify_class"
        if any(w in message_lower for w in [
            "edit gas", "update gas", "modify gas", "change gas",
            "add to gas", "fix gas", "gas function", "apps script",
            "google apps script", "add function to gas",
            "write gas", "gas code", "backend code"
        ]):
            return "write_gas"
        
        if any(w in message_lower for w in [
            "read code", "show code", "how is", "how does", "how was",
            "explain the code", "what does", "show me how", "read the file",
            "look at the code", "check the code", "what's in"
        ]):
            return "read_code"

        if any(w in message_lower for w in [
            "suggest", "improve", "improvement", "what's wrong",
            "whats wrong", "optimize", "fix", "better", "analyze",
            "analyse", "review", "audit", "check my code",
            "what can be better", "recommendations"
        ]):
            return "suggest"

        if any(w in message_lower for w in [
            "issue", "problem", "bug", "error", "broken",
            "not working", "failing", "wrong with", "deep dive",
            "investigate", "look into"
        ]):
            return "analyze_issue"

        if any(w in message_lower for w in [
            "add a feature", "add feature", "write code", "create a function",
            "build a", "implement", "code a", "write a function",
            "add to the code", "update the code", "modify the code",
            "change the code", "fix the code", "patch",
            "add a", "add an", "i want u to add", "i want you to add",
            "can you add", "please add", "add email", "add field",
            "add button", "add page", "add tab", "add section",
            "add column", "add form", "add input", "add option",
            "create", "make a", "make an", "build me", "generate a"
        ]):
            return "write_code"

        return "chat"

    def _execute_intent(self, intent: str, db, df_all, reps_list, all_feedback, all_anns) -> str:
        """Execute a detected intent and return a formatted result string."""

        if intent == "count_students":
            count = len(df_all) if df_all is not None and not df_all.empty else 0
            dept_col = next((c for c in ["Department", "department", "dept"] if c is not None and df_all is not None and c in df_all.columns), None)
            if dept_col and df_all is not None:
                breakdown = df_all[dept_col].value_counts().to_dict()
                breakdown_text = "\n".join([f"  • {k}: {v}" for k, v in breakdown.items()])
                return f"📊 **Student Count**\n\nTotal: **{count} students**\n\nBy Department:\n{breakdown_text}"
            return f"📊 Total students registered: **{count}**"

        if intent == "list_students":
            if df_all is None or df_all.empty:
                return "📭 No students registered yet."
            rows = df_all.head(20)
            lines = []
            for _, row in rows.iterrows():
                name = row.get("Student Name", row.get("student_name", "Unknown"))
                reg = row.get("Reg Number", row.get("reg_number", ""))
                dept = row.get("Department", row.get("department", ""))
                lines.append(f"• {name} | {reg} | {dept}")
            result = "\n".join(lines)
            total = len(df_all)
            return f"👥 **Students (showing first 20 of {total}):**\n\n{result}"

        if intent == "list_reps":
            if not reps_list:
                return "📭 No class rep accounts created yet."
            lines = []
            for r in reps_list:
                name = r.get("rep_name", r.get("name", "Unknown"))
                dept = r.get("dept", r.get("department", ""))
                year = r.get("year", "")
                lines.append(f"👑 {name} — {dept} · {year}")
            result = "\n".join(lines)
            return f"**Class Rep Accounts ({len(reps_list)}):**\n\n{result}"

        if intent == "show_feedback":
            if not all_feedback:
                return "📭 No feedback messages yet."
            lines = []
            for fb in all_feedback[:10]:
                if isinstance(fb, list) and len(fb) >= 5:
                    lines.append(f"• [{fb[2]}]: {fb[4][:80]}...")
            result = "\n".join(lines)
            return f"📬 **Recent Feedback (showing 10 of {len(all_feedback)}):**\n\n{result}"

        if intent == "show_announcements":
            if not all_anns:
                return "📭 No announcements yet."
            lines = []
            for ann in all_anns[:10]:
                if isinstance(ann, dict):
                    lines.append(f"• [{ann.get('timestamp','')}] {ann.get('text','')[:80]}")
            result = "\n".join(lines)
            return f"📢 **Recent Announcements (showing 10 of {len(all_anns)}):**\n\n{result}"

        if intent == "list_departments":
            try:
                # Import config and get departments
                import config
                depts = config.get_departments()
                if not depts:
                    return "📭 No departments configured."
                lines = []
                for code, info in depts.items():
                    lines.append(f"• {info['name']} ({code})")
                result = "\n".join(lines)
                return f"🏛️ **Departments ({len(depts)}):**\n\n{result}"
            except Exception as e:
                return f"❌ Could not load departments: {str(e)}"

        if intent == "portal_status":
            student_count = len(df_all) if df_all is not None and not df_all.empty else 0
            rep_count = len(reps_list) if reps_list else 0
            feedback_count = len(all_feedback) if all_feedback else 0
            ann_count = len(all_anns) if all_anns else 0
            key_count = _key_manager.total_keys()

            status = "🟢 Healthy" if key_count > 0 else "🔴 No AI Keys"

            return (
                f"🖥️ **Portal Status Report**\n\n"
                f"Overall: {status}\n\n"
                f"📊 Data:\n"
                f"  • Students: {student_count}\n"
                f"  • Class Reps: {rep_count}\n"
                f"  • Feedback Messages: {feedback_count}\n"
                f"  • Announcements: {ann_count}\n\n"
                f"🤖 AI Engine:\n"
                f"  • Gemini Keys Active: {key_count}\n"
                f"  • Model: Gemini 2.5 Flash\n"
                f"  • Fallback Chain: Groq → Mistral → HuggingFace → Cloudflare\n\n"
                f"⚡ All systems operational."
            )

        if intent == "list_sheets":
            try:
                if db and hasattr(db, 'list_sheets'):
                    sheets = db.list_sheets()
                else:
                    sheets = []
                if not sheets:
                    return "📭 No sheets found."
                lines = [f"• {s.get('name','')} ({s.get('rows',0)} rows)" for s in sheets]
                return f"📋 **Google Sheets ({len(sheets)}):**\n\n" + "\n".join(lines)
            except Exception as e:
                return f"❌ Could not load sheets: {str(e)}"

        if intent == "add_department":
            return "NEEDS_FORM:add_department"
        if intent == "assign_rep":
            return "NEEDS_FORM:assign_rep"
        if intent == "delete_department":
            return "NEEDS_FORM:delete_department"
        if intent == "delete_rep":
            return "NEEDS_FORM:delete_rep"
        if intent == "reset_rep_password":
            return "NEEDS_FORM:reset_rep_password"
        if intent == "broadcast_announcement":
            return "NEEDS_FORM:broadcast_announcement"
        if intent == "post_announcement":
            return "NEEDS_FORM:post_announcement"
        if intent == "delete_announcement":
            return "NEEDS_FORM:delete_announcement"
        if intent == "delete_student":
            return "NEEDS_FORM:delete_student"
        if intent == "assign_group":
            return "NEEDS_FORM:assign_group"
        if intent == "post_timetable":
            return "NEEDS_FORM:post_timetable"
        if intent == "delete_timetable":
            return "NEEDS_FORM:delete_timetable"
        if intent == "notify_class":
            return "NEEDS_FORM:notify_class"
        if intent == "read_code":
            return None
        return None

    def chat(
        self,
        user_message: str,
        chat_history: list,
        db=None,
        df_all=None,
        reps_list=None,
        all_feedback=None,
        all_anns=None
    ) -> str:
        """
        Main chat method — Layer 1 + Layer 2.
        Detects intent first, executes portal actions if matched,
        otherwise falls through to conversational AI.
        """
        if not _key_manager.has_keys():
            return "⚠️ No API keys found. Please add GEMINI_KEY_1 to your secrets.toml."

        # ── Layer 2: Intent detection & execution ─────────────
        intent = self._detect_intent(user_message)
        if intent != "chat":
            action_result = self._execute_intent(
                intent, db, df_all, reps_list, all_feedback, all_anns
            )
            if action_result:
                # Handle form-based intents
                if action_result.startswith("NEEDS_FORM:"):
                    form_type = action_result.replace("NEEDS_FORM:", "")
                    st.session_state["master_ai_pending_form"] = {
                        "type": form_type,
                        "triggered_by": user_message
                    }
                    form_messages = {
                        "add_department"      : "✅ Let's add a new department! Fill in the form below.",
                        "assign_rep"          : "✅ Let's assign a class rep! Fill in the form below.",
                        "delete_department"   : "⚠️ I'll help you delete a department. Confirm carefully below — this cannot be undone.",
                        "delete_rep"          : "⚠️ I'll help you remove a class rep. Confirm below.",
                        "reset_rep_password"  : "✅ Let's reset a rep's password. Fill in the form below.",
                        "broadcast_announcement": "📢 Let's broadcast to all departments! Fill in the form below.",
                        "post_announcement"   : "📢 Let's post an announcement! Fill in the form below.",
                        "delete_announcement" : "⚠️ I'll help you delete an announcement. Confirm below.",
                        "delete_student"      : "⚠️ I'll help you remove a student. Confirm carefully — this cannot be undone.",
                        "assign_group"        : "✅ Let's assign a student to a group! Fill in the form below.",
                        "post_timetable"      : "✅ Let's add a timetable entry! Fill in the form below.",
                        "delete_timetable"    : "⚠️ I'll help you delete a timetable entry. Confirm below.",
                        "notify_class"        : "📱 Let's send a WhatsApp notification! Fill in the form below.",
                    }
                    return (
                        form_messages.get(form_type, "✅ Fill in the form below.") +
                        "\n\n⬇️ **Scroll down to the form.**"
                    )

                # Pass normal result through AI to make it feel natural
                portal_context = self._build_portal_context(db, df_all, reps_list)
                polish_prompt = (
                    f"{portal_context}\n\n"
                    f"Alia's request: \"{user_message}\"\n\n"
                    f"Master AI's response: \"{action_result}\"\n\n"
                    f"Polish the response to make it sound natural and conversational. "
                    f"Keep the meaning intact. Do not add new information. "
                    f"Return only the polished text."
                )
                config = types.GenerateContentConfig(
                    system_instruction=MASTER_AI_SYSTEM_PROMPT,
                    temperature=0.4,
                    max_output_tokens=1000
                )
                response = _call_with_retry(self.model, polish_prompt, config)
                if len(chat_history) > 0 and len(chat_history) % 10 == 0:
                    try:
                        self.memory.extract_and_save_memories(chat_history, db)
                    except Exception as e:
                        print(f"[Memory] Auto-save error: {e}")
                return response

        # ── Layer 3 + 4: Code reading & Suggestions ───────────
        # Re-detect intent in case it was "chat" before
        intent = self._detect_intent(user_message)
        code_context = ""

        # Handle suggestion intent directly
        if intent == "suggest":
            specific_file = self._detect_code_file(user_message)
            target = specific_file if specific_file else "full_portal"
            return self.suggest_improvements(
                target=target,
                db=db,
                df_all=df_all,
                reps_list=reps_list,
                all_feedback=all_feedback,
                all_anns=all_anns
            )

        # Handle deep issue analysis
        if intent == "analyze_issue":
            return self.analyze_specific_issue(
                issue=user_message,
                db=db,
                df_all=df_all,
                reps_list=reps_list
            )
        
        # Handle GAS editing
        if intent == "write_gas":
            result = self.write_gas_change(request=user_message)
            if "error" in result:
                return result["error"]
            st.session_state["master_ai_pending_change"] = result
            validation = result.get("validation", {})
            return (
                f"✅ **GAS code written for `{result['target_file']}`**\n\n"
                f"{validation.get('summary','')}\n\n"
                f"⬇️ **Scroll down to review and approve.** Nothing is deployed yet."
            )

        # Handle code writing — store result in session for approval UI
        if intent == "write_code":
            result = self.write_code_change(
                request=user_message,
                db=db,
                df_all=df_all,
                reps_list=reps_list
            )
            if "error" in result:
                return result["error"]
            st.session_state["master_ai_pending_change"] = result

            # Confirmation message — direct, no narration
            validation = result.get("validation", {})
            val_summary = validation.get("summary", "")
            lines_orig = validation.get("lines_original", "?")
            lines_new = validation.get("lines_new", "?")

            return (
                f"✅ **Code written for `{result['target_file']}`**\n\n"
                f"**What was done:** {result.get('explanation', result['request'])}\n\n"
                f"{val_summary}\n"
                f"📄 {lines_orig} lines → {lines_new} lines\n\n"
                f"⬇️ **Scroll down to review, approve or reject the changes.** Nothing is deployed yet."
            )

        # Handle code reading
        if intent == "read_code":
            specific_file = self._detect_code_file(user_message)
            code_context = self._read_codebase(specific_file)

        # ── Layer 1: Normal conversational chat ───────────────
        portal_context = self._build_portal_context(db, df_all, reps_list)

        history_block = ""
        if chat_history:
            for turn in chat_history[-10:]:
                role = "Alia" if turn["role"] == "user" else "Master AI"
                history_block += f"{role}: {turn['content']}\n"
            history_block = f"=== CONVERSATION HISTORY ===\n{history_block}\n=== END HISTORY ===\n"

        # code_context may or may not be set depending on intent
        code_section = code_context if code_context else ""

        full_prompt = (
            f"{portal_context}\n"
            f"{code_section}\n"
            f"{history_block}\n"
            f"=== ALIA'S MESSAGE ===\n{user_message}\n"
            f"=== END MESSAGE ===\n\n"
            f"Respond as the Master Super Admin AI. "
            f"If code context is provided, analyze it and answer directly from the code. "
            f"Be specific about what you find in the actual files."
        )

        config = types.GenerateContentConfig(
            system_instruction=MASTER_AI_SYSTEM_PROMPT,
            temperature=0.5,
            max_output_tokens=3000
        )

        response = _call_with_retry(self.model, full_prompt, config)

        # Auto-save memories every 10 messages
        if len(chat_history) > 0 and len(chat_history) % 10 == 0:
            try:
                self.memory.extract_and_save_memories(chat_history, db)
            except Exception as e:
                print(f"[Memory] Auto-save error: {e}")

        return response

      
    def get_greeting(self, df_all=None, reps_list=None) -> str:
        """Generate a smart greeting when Alia opens the Master AI tab."""
        if not _key_manager.has_keys():
            return "⚠️ No API keys configured."

        student_count = len(df_all) if df_all is not None and not df_all.empty else 0
        rep_count = len(reps_list) if reps_list else 0

        prompt = (
            f"Greet Alia, the Super Admin of the SMART UNIVERSITY APP.\n"
            f"Current portal stats: {student_count} students registered, {rep_count} class reps.\n"
            f"AI keys active: {_key_manager.total_keys()}\n\n"
            f"Give a short, smart, motivating greeting (3-4 sentences max). "
            f"Mention the portal stats naturally. Tell her you're ready to help. "
            f"Be warm but professional. End with asking what she needs today."
        )

        config = types.GenerateContentConfig(
            system_instruction=MASTER_AI_SYSTEM_PROMPT,
            temperature=0.7,
            max_output_tokens=200
        )
        result = _call_with_retry(self.model, prompt, config)
        # Strip any accidental HTML
        import re
        result = re.sub(r'<[^>]+>', '', result)
        return result