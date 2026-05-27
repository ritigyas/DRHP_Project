import re

class DocumentClassifier:
    @staticmethod
    def classify(content: str, filename: str = "") -> dict:
        """
        Classifies a document based on its textual content and optional filename.
        Returns a dict with:
        - document_type: "SH_7" | "BOARD_RESOLUTION" | "EGM_NOTICE" | "MOA_CLAUSE_V" | "UNKNOWN"
        - filing_status: "OFFICIAL" | "DRAFT"
        - event_id: "Event1" | "Event2" | "Event3" | "UNKNOWN"
        """
        content_upper = content.upper()
        
        # 1. Document Type Classification
        doc_type = "UNKNOWN"
        filename_upper = filename.upper()
        
        if "SH-7" in filename_upper or "SH7" in filename_upper:
            doc_type = "SH_7"
        elif "BOARD_RESOLUTION" in filename_upper or "BOARD" in filename_upper:
            doc_type = "BOARD_RESOLUTION"
        elif "EGM" in filename_upper or "NOTICE" in filename_upper:
            doc_type = "EGM_NOTICE"
        elif "MOA" in filename_upper or "MEMORANDUM" in filename_upper:
            doc_type = "MOA_CLAUSE_V"
            
        # Content fallback
        if doc_type == "UNKNOWN":
            if "FORM SH-7" in content_upper and "MINISTRY OF CORPORATE AFFAIRS" in content_upper:
                doc_type = "SH_7"
            elif "BOARD OF DIRECTORS" in content_upper and ("RESOLUTION PASSED AT" in content_upper or "CERTIFIED TRUE COPY" in content_upper or "RESOLVED THAT" in content_upper):
                doc_type = "BOARD_RESOLUTION"
            elif "NOTICE OF EXTRAORDINARY GENERAL MEETING" in content_upper:
                doc_type = "EGM_NOTICE"
            elif "MEMORANDUM OF ASSOCIATION" in content_upper and ("CLAUSE V" in content_upper or re.search(r'\bV\.\s+THE\s+AUTHORISED\s+SHARE\s+CAPITAL\b', content_upper)):
                doc_type = "MOA_CLAUSE_V"

        # 2. Filing Status Classification
        status = "OFFICIAL"
        if "DRAFT" in content_upper or "PENDING" in content_upper or "UNSIGNED" in content_upper or "FOR DISCUSSION ONLY" in content_upper:
            status = "DRAFT"
        elif "DRAFT" in filename.upper():
            status = "DRAFT"

        # 3. Event / Package classification based on contents or filename
        event_id = "UNKNOWN"
        if "EVENT1" in filename.upper() or "PACKAGE_1" in filename.upper() or "PACKAGE 1" in filename.upper():
            event_id = "Event1"
        elif "EVENT2" in filename.upper() or "PACKAGE_2" in filename.upper() or "PACKAGE 2" in filename.upper():
            event_id = "Event2"
        elif "EVENT3" in filename.upper() or "PACKAGE_3" in filename.upper() or "PACKAGE 3" in filename.upper():
            event_id = "Event3"
        else:
            # Try to match based on content dates or amounts
            if "2023" in content_upper:
                event_id = "Event1"
            elif "2024" in content_upper:
                event_id = "Event2"
            elif "2025" in content_upper:
                event_id = "Event3"

        return {
            "document_type": doc_type,
            "filing_status": status,
            "event_id": event_id
        }
