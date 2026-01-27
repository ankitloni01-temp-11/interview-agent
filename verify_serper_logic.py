import json
from unittest.mock import MagicMock, patch
from src.gemini_parser import GeminiParser

def test_serper_fallback():
    # Mock data
    mock_pdf_content = b"fake pdf content"
    mock_cv_text = "John Doe\nSoftware Engineer"
    mock_gemini_json = {
        "contact_information": {
            "name": "John Doe",
            "email": "john@example.com",
            "linkedin": None,
            "github": None
        }
    }
    
    with patch('src.gemini_parser.GeminiParser.extract_text_from_pdf', return_value=mock_cv_text):
        with patch('google.generativeai.GenerativeModel.generate_content') as mock_gen:
            # Mock Gemini response
            mock_gen_response = MagicMock()
            mock_gen_response.text = json.dumps(mock_gemini_json)
            mock_gen.return_value = mock_gen_response
            
            with patch('src.serper_service.SerperService.search_profile') as mock_serper:
                # Mock Serper results
                def side_effect(name, platform):
                    if platform == "linkedin":
                        return "https://linkedin.com/in/johndoe"
                    if platform == "github":
                        return "https://github.com/johndoe"
                    return None
                mock_serper.side_effect = side_effect
                
                # Run parser
                parser = GeminiParser()
                result = parser.parse_cv(mock_pdf_content)
                
                # Verify
                print("Parsed Result with Serper Fallback:")
                print(json.dumps(result, indent=2))
                
                contact = result.get("contact_information", {})
                assert contact.get("linkedin") == "https://linkedin.com/in/johndoe"
                assert contact.get("github") == "https://github.com/johndoe"
                print("\n[✓] Fallback logic verified successfully!")

if __name__ == "__main__":
    try:
        test_serper_fallback()
    except Exception as e:
        print(f"\n[✗] Verification failed: {e}")
        import traceback
        traceback.print_exc()
