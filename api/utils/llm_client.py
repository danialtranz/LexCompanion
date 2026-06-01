



import json
import httpx
import openai
from api.utils.logger import logger

import os
from dotenv import load_dotenv

load_dotenv()

prompt_template = """
Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam.

Nhiệm vụ:
Từ nội dung trang bìa của văn bản, hãy trích xuất thông tin sau:

1. Loại văn bản (doc_type):
   - "luat"
   - "nghi_dinh"
   - "thong_tu"

2. Tên văn bản (doc_name):
   - Ví dụ: "Nghị định số 23/2026/NĐ-CP"

3. Số văn bản (doc_number):
   - Ví dụ: "23/2026"

4. Năm ban hành (doc_year)

5. Mục đích văn bản (doc_purpose):
   - "ban_hanh" (nếu là văn bản mới)
   - "sua_doi" (nếu có từ: sửa đổi, bổ sung)

6. Các căn cứ pháp lý (legal_bases):
   - Trích xuất tất cả các dòng bắt đầu bằng "Căn cứ"
   - Với mỗi căn cứ, trả về:
     - type: "luat" | "nghi_dinh" | "khac"
     - name: tên văn bản
     - number: số văn bản (ví dụ: 63/2025/QH15)

⚠️ Lưu ý:
- Chỉ trả về JSON, không giải thích
- Chuẩn hóa text về lowercase và snake_case nếu cần
- Nếu không có thông tin thì trả về null hoặc []

Trả về theo format:

{
  "doc_type": "...",
  "doc_name": "...",
  "doc_number": "...",
  "doc_year": "...",
  "doc_purpose": "...",
  "legal_bases": [
    {
      "type": "...",
      "name": "...",
      "number": "..."
    }
  ]
}
"""

prompt_template_2 = """
Bạn là chuyên gia phân tích văn bản pháp luật Việt Nam.,Đây là đoạn cuối của 1 văn bản pháp 
luật chuẩn bị được ban hành .Nếu có tên người được viết ở dạng in hoa chữ cái đầu thì đó chính là người kí .

Nhiệm vụ:
Từ nội dung cuối cùng của văn bản, hãy trích xuất thông tin sau:

1. Vai trò của người ký (signer_role):
   - "chủ tịch quốc hội"
   - "thủ tướng chính phủ"
   - "bộ trưởng"
   - "thứ trưởng"
   - "..."

Trả về theo format:

{
  "signer_role": "..."
  "signer_name": "..."
}
"""
config = {
    "model_name": os.getenv("LLM_MODEL", "gpt-4o-mini"),
    "api_key": os.getenv("OPENAI_API_KEY"),
    "base_url": os.getenv("OPENAI_BASE_URL"),
    "timeout": 300,
    "max_tokens": 1000,
    "temperature": 0.5,
    "top_p": 1,
    "frequency_penalty": 0,
    "presence_penalty": 0,
}
def check_json_response(response):
    try:
        json.loads(response)
        return True
    except Exception as e:
        return False
    return True
class LLMProvider:
    def __init__(self, config):
        self.model_name = config.get("model_name")
        self.api_key = config.get("api_key")
        if "base_url" in config:
            self.base_url = config.get("base_url")
        else:
            self.base_url = config.get("url")
        timeout = config.get("timeout", 300)
        self.timeout = int(timeout) if timeout else 300

        param_defaults = {
            "max_tokens": int,
            "temperature": lambda x: round(float(x), 1),
            "top_p": lambda x: round(float(x), 1),
            "frequency_penalty": lambda x: round(float(x), 1),
        }
        self.client = openai.OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=httpx.Timeout(self.timeout))
        for param, converter in param_defaults.items():
            value = config.get(param)
            try:
                setattr(
                    self,
                    param,
                    converter(value) if value not in (None, "") else None,
                )
            except (ValueError, TypeError):
                setattr(self, param, None)

        logger.debug(
            f"LLM parameters initialized: {self.temperature}, {self.max_tokens}, {self.top_p}, {self.frequency_penalty}"
        )

        

    @staticmethod
    def normalize_dialogue(dialogue):
        """Auto-fix missing content messages in dialogue"""
        for msg in dialogue:
            if "role" in msg and "content" not in msg:
                msg["content"] = ""
        return dialogue

    def response(self, dialogue, prompt_template_number=1, **kwargs):
        try:
            dialogue = self.normalize_dialogue(dialogue)
            ### them system prompt vao dau dialogue
            if prompt_template_number == 1:
                dialogue.insert(0, {"role": "system", "content": prompt_template})
            elif prompt_template_number == 2:
                dialogue.insert(0, {"role": "system", "content": prompt_template_2})
            request_params = {
                "model": self.model_name,
                "messages": dialogue,
                "stream": False,
            }
            llm_options = kwargs.get("llm_options", {}) or {}

            # Priority:
            # 1) individual parameters in kwargs (max_tokens / temperature / top_p / frequency_penalty)
            # 2) corresponding keys in llm_options
            # 3) instance default values (self.xxx)
            optional_params = {}
            for key in ["max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                value = kwargs.get(key, None)
                if value is None:
                    value = llm_options.get(key, getattr(self, key, None))
                optional_params[key] = value

            for key, value in optional_params.items():
                if value is not None:
                    request_params[key] = value
           
            
            responses = self.client.chat.completions.create(**request_params)
            ## in ra input token va output token 
            logger.info(f"Input tokens: {responses.usage.prompt_tokens}")
            logger.info(f"Output tokens: {responses.usage.completion_tokens}")
            ### check xem có trả đúng về json và các field theo yêu cầu không 
            try:
                ### neu prompt template la 1 thi check rieng cho prompt template 1
                if prompt_template_number == 1:
                    if check_json_response(responses.choices[0].message.content):
                        return json.loads(responses.choices[0].message.content)
                    else:
                        logger.error(f"Error in json parsing: {responses.choices[0].message.content}")
                        return None
                ### neu prompt template la 2 thi check rieng cho prompt template 2
                elif prompt_template_number == 2:
                    if check_json_response(responses.choices[0].message.content):
                        return json.loads(responses.choices[0].message.content)
                    else:
                        logger.error(f"Error in json parsing: {responses.choices[0].message.content}")
                        return None
                
            except Exception as e:
                logger.error(f"Error in json parsing: {e}")
                return None
        except Exception as e:
            logger.error(f"Error in response generation: {e}")
            return None

    def chat_text(
        self,
        dialogue: list[dict],
        *,
        system_prompt: str | None = None,
        **kwargs,
    ) -> str | None:
        """OpenAI chat completion; returns plain text (no JSON validation)."""
        try:
            dialogue = self.normalize_dialogue(dialogue)
            messages: list[dict] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.extend(dialogue)

            request_params: dict = {
                "model": kwargs.get("model") or self.model_name,
                "messages": messages,
                "stream": False,
            }
            llm_options = kwargs.get("llm_options", {}) or {}
            for key in ["max_tokens", "temperature", "top_p", "frequency_penalty", "presence_penalty"]:
                value = kwargs.get(key, llm_options.get(key, getattr(self, key, None)))
                if value is not None:
                    request_params[key] = value

            responses = self.client.chat.completions.create(**request_params)
            if responses.usage:
                logger.info(
                    "chat_text tokens: prompt={} completion={}",
                    responses.usage.prompt_tokens,
                    responses.usage.completion_tokens,
                )
            return responses.choices[0].message.content
        except Exception as e:
            logger.error(f"Error in chat_text: {e}")
            return None


if __name__ == "__main__":
    llm_client = LLMProvider(config)
    response = llm_client.response(dialogue=[{"role": "user", "content": """CHÍNH PHỦ
-------

CỘNG HÒA XÃ HỘI CHỦ NGHĨA VIỆT NAM
Độc lập - Tự do - Hạnh phúc
---------------

Số: 23/2026/NĐ-CP

Hà Nội, ngày 17 tháng 01 năm 2026

 

NGHỊ ĐỊNH

SỬA ĐỔI, BỔ SUNG MỘT SỐ ĐIỀU CỦA CÁC NGHỊ ĐỊNH TRONG LĨNH VỰC TÀI NGUYÊN NƯỚC

Căn cứ Luật Tổ chức Chính phủ số 63/2025/QH15;

Căn cứ Luật Tổ chức chính quyền địa phương số 72/2025/QH15;

Căn cứ Luật Tài nguyên nước số 28/2023/QH15;

Căn cứ Luật sửa đổi, bổ sung một số điều của 15 luật trong lĩnh vực nông nghiệp và môi trường số 146/2025/QH15;

Theo đề nghị của Bộ trưởng Bộ Nông nghiệp và Môi trường;

Chính phủ ban hành Nghị định sửa đổi, bổ sung một số điều của các nghị định trong lĩnh vực tài nguyên nước."""}])
    logger.info(response)