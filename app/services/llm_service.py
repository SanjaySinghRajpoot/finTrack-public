import os
import json
import re
from openai import OpenAI
from fastapi import HTTPException

from app.utils.utils import create_processed_email_data


class LLMService:
    """
    LLMService encapsulates the logic for:
      - Interacting with the Gemini API
      - Parsing and validating structured JSON responses
      - Handling multiple text inputs in batches
    """

    def __init__(self, user_id, db):
        try:
            self.api_key = os.getenv("OPENAI_API_KEY")
            self.db = db
            if not self.api_key:
                raise ValueError("OPENAI_API_KEY environment variable is not set")

            self.client = OpenAI(
                api_key=self.api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )

            self.schema = {
                "is_processing_valid": {"type": "boolean", "default": False},
                "email_id": {"type":"integer"},
                "user_id": {"type": "integer"},
                "document_type": {
                    "type": "string",
                    "description": "Type of document",
                    "enum": ["invoice", "bill", "emi", "payment_receipt", "tax_invoice", "credit_note", "debit_note",
                             "other"]
                },
                "title": {"type": "string", "description": "Document title or name"},
                "description": {"type": "string", "description": "Brief description of the document"},
                "document_number": {"type": "string",
                                    "description": "Invoice number, bill number, or document reference number"},
                "reference_id": {"type": "string", "description": "Additional reference ID or order number"},
                "issue_date": {"type": "string", "format": "date",
                               "description": "Date when the document was issued (YYYY-MM-DD)"},
                "due_date": {"type": "string", "format": "date", "description": "Payment due date (YYYY-MM-DD)"},
                "payment_date": {"type": "string", "format": "date",
                                 "description": "Date when payment was made (YYYY-MM-DD)"},
                "amount": {"type": "number", "description": "Total amount of the document"},
                "currency": {"type": "string", "description": "Currency code (default: INR)", "default": "INR"},
                "is_paid": {"type": "boolean", "description": "Whether the document has been paid", "default": False},
                "payment_method": {"type": "string",
                                   "description": "Method of payment (cash, card, bank transfer, etc.)"},
                "vendor_name": {"type": "string", "description": "Name of the vendor or company"},
                "vendor_gstin": {"type": "string", "description": "Vendor's GST identification number"},
                "category": {"type": "string", "description": "Category of expense or document type"},
                "tags": {"type": "array", "items": {"type": "string"},
                         "description": "List of tags for categorization"},
                "metadata": {"type": "array",
                             "description": "List of all relevant document metadata to assist in later processing."},

            }

            self.required_fields = ["title", "amount"]

            self.base_prompt_batch = """
            You are given two inputs:
            1. A JSON schema
            2. Multiple text contents, each enclosed between ---text--start--- and ---text--end---
            
            Your task:
            - For each text block:
              - Determine if the text is relevant to the JSON schema.
              - If irrelevant or incomplete, set `is_processing_valid` to false and leave other fields empty.
              - Otherwise, extract the relevant data and fill the schema.
            - Return the output as a JSON array (one object per text block).
            - title as per your understanding if not available
            - Follow schema strictly.
            - Wrap the response in ```json code block.
            
            JSON Schema:
            {schema}
            
            Text Contents:
            {texts}
            """

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Initialization error: {str(e)}")


    def _saving_llm_response(self, processed_email_data):
        try:
            for data in processed_email_data:
                email_id = data.get("email_id")
                user_id = data.get("user_id")
                
                # Get the email to retrieve source_id
                email = self.db.get_email_by_pk(email_id)
                if not email or not email.source_id:
                    print(f"Warning: Email with id {email_id} not found or has no source_id, skipping")
                    continue
                
                data_obj = create_processed_email_data(
                    user_id=user_id, 
                    source_id=email.source_id,  # Pass source_id from email
                    email_id=email_id,          # Keep for backward compatibility
                    data=data
                )
                self.db.save_proccessed_email_data(data_obj)
        except Exception as e:
            raise e

    def llm_batch_processing(self, emails_array: list[dict]) -> list[dict]:
        """
        Processes all emails in a batch using the LLM service.
        - If an email has an attachment, pick the first attachment's `text_content`.
        - Otherwise, use the `body`.
        - Accumulates all text into a single formatted string.
        - Calls `call_gemini()` once for the entire batch.
        Returns a list of validated JSON objects from the LLM.
        """
        try:
            if not emails_array or not isinstance(emails_array, list):
                raise HTTPException(status_code=400, detail="emails_array must be a non-empty list")

            accumulated_text = ""

            for idx, email in enumerate(emails_array):
                try:
                    if not isinstance(email, dict):
                        raise ValueError(f"Invalid email data at index {idx}")

                    has_attachments = email.get("has_attachments", False)
                    attachments = email.get("attachments", [])

                    if has_attachments and isinstance(attachments, list) and attachments:
                        # Pick text_content from the first attachment
                        first_attachment = attachments[0]
                        text_chunk = first_attachment.get("text_content", "").strip()
                    else:
                        # Fallback to email body
                        text_chunk = (email.get("body") or "").strip()

                    if not text_chunk:
                        # Skip empty emails
                        continue

                    # replace this with source id
                    email_id = email.get("email_id")
                    user_id = email.get("user_id")

                    # Append with clear delimiters for LLM parsing
                    accumulated_text += f"\n----email{idx + 1}-start---email_id:\n{email_id}\n---user_id:\n{user_id}\n---\n{text_chunk}\n----email{idx + 1}-end----\n"

                except Exception as inner_error:
                    # Skip this email but continue with others
                    print(f"[WARN] Skipping email index {idx}: {inner_error}")
                    continue

            if not accumulated_text.strip():
                raise HTTPException(status_code=400, detail="No valid email content found to process")


            try:
                results = self.llm_processing(accumulated_text)
            except Exception as llm_error:
                raise HTTPException(status_code=500, detail=f"LLM processing failed: {llm_error}")

            # ------------------------ move to background task ---------------------------------------------
            #               Send the entire accumulated string to the LLM
            self._saving_llm_response(results)

            email_ids = [r["email_id"] for r in results if "email_id" in r]

            self.db.update_email_status(email_ids)

            return results

        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in _llm_batch_processing: {e}")

    def _validate_json(self, data):
        """Validate a single or list of JSON objects against schema."""
        try:
            if isinstance(data, dict):
                data = [data]

            if not isinstance(data, list):
                raise ValueError("Data must be an array of JSON objects")

            validated_list = []

            for idx, item in enumerate(data):
                if not isinstance(item, dict):
                    raise ValueError(f"Item at index {idx} is not a JSON object")

                validated = {}
                for key, rules in self.schema.items():
                    value = item.get(key, rules.get("default"))
                    expected_type = rules["type"]

                    if key in self.required_fields and (value is None or value == ""):
                        raise ValueError(f"Missing required field: {key} in item {idx}")

                    if value is not None:
                        if expected_type == "string" and not isinstance(value, str):
                            raise ValueError(f"Field {key} in item {idx} must be a string")
                        elif expected_type == "number" and not isinstance(value, (int, float)):
                            raise ValueError(f"Field {key} in item {idx} must be a number")
                        elif expected_type == "boolean" and not isinstance(value, bool):
                            raise ValueError(f"Field {key} in item {idx} must be a boolean")
                        elif expected_type == "array":
                            if not isinstance(value, list):
                                raise ValueError(f"Field {key} in item {idx} must be an array")
                            if "items" in rules and rules["items"]["type"] == "string":
                                if not all(isinstance(i, str) for i in value):
                                    raise ValueError(f"All items in {key} (item {idx}) must be strings")

                    validated[key] = value

                extra_keys = set(item.keys()) - set(self.schema.keys())
                if extra_keys:
                    raise ValueError(f"Extra keys not allowed in item {idx}: {extra_keys}")

                validated_list.append(validated)

            return validated_list
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"JSON validation failed: {str(e)}")

    def _build_text_block(self, texts: list[str]) -> str:
        """Builds delimited text block for LLM input."""
        try:
            parts = []
            for i, t in enumerate(texts, start=1):
                parts.append(f"---text{i}-start---\n{t.strip()}\n---text{i}-end---")
            return "\n\n".join(parts)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error while building text block: {str(e)}")

    def llm_processing(self, texts: list[str]) -> list[dict]:
        """
        Orchestrates the full LLM processing pipeline.
        """
        try:
            self._validate_texts(texts)

            formatted_prompt = self._format_prompt(texts)

            response = self._call_gemini_api(formatted_prompt)

            response_text = self._extract_response_text(response)

            parsed_json = self._parse_json_response(response_text)

            validated_data = self._process_and_validate(parsed_json)

            return validated_data

        except HTTPException as e:
            raise e
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Unexpected error in llm_processing: {e}")

        # ------------------ Sub Functions ------------------

    def _validate_texts(self, texts: list[str]):
        if not texts:
            raise HTTPException(status_code=400, detail="No text contents provided")

    def _format_prompt(self, texts: list[str]) -> str:
        return self.base_prompt_batch.format(
            schema=json.dumps(self.schema, indent=2),
            texts=texts
        )

    def _call_gemini_api(self, formatted_prompt: str):
        try:
            return self.client.chat.completions.create(
                model="gemini-2.0-flash-exp",
                messages=[
                    {"role": "system", "content": "You are a JSON parser."},
                    {"role": "user", "content": formatted_prompt}
                ],
                temperature=0,
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Gemini API call failed: {str(e)}")

    def _extract_response_text(self, response):
        if not response.choices or not response.choices[0].message:
            raise HTTPException(status_code=500, detail="No valid response from Gemini")

        return response.choices[0].message.content.strip()

    def _parse_json_response(self, response_text: str):
        json_text = self._extract_json(response_text)
        try:
            return json.loads(json_text)
        except json.JSONDecodeError as e:
            raise HTTPException(status_code=500, detail=f"Gemini returned invalid JSON: {e}")

    def _process_and_validate(self, parsed: list[dict]) -> list[dict]:
        all_results = []
        for json_txt in parsed:
            if json_txt["is_processing_valid"]:
                validated = self._validate_json(parsed)
                all_results.extend(validated)
        return all_results

        # ------------------ Existing Utilities ------------------

    def _extract_json(self, response_text: str) -> str:
        """Extract JSON from code blocks."""
        try:
            json_pattern = r'```(?:json)?\s*\n?(.*?)\n?```'
            match = re.search(json_pattern, response_text, re.DOTALL)
            if match:
                return match.group(1).strip()

            json_pattern_direct = r'\[.*\]'
            match_direct = re.search(json_pattern_direct, response_text, re.DOTALL)
            if match_direct:
                return match_direct.group(0).strip()

            return response_text.strip()
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"JSON extraction failed: {str(e)}")
