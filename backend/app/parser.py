import re
from datetime import datetime

class DocumentParser:
    @staticmethod
    def clean_number(value_str: str) -> int:
        """Cleans and converts a number string (e.g., '1,50,00,000', 'Rs. 50,00,000') into an integer."""
        if not value_str or value_str.strip().upper() == "NIL":
            return 0
        cleaned = re.sub(r'[^\d]', '', value_str)
        return int(cleaned) if cleaned else 0

    @staticmethod
    def normalize_date(date_str: str) -> str:
        """
        Normalizes various date formats into YYYY-MM-DD.
        Supports:
        - DD/MM/YYYY (e.g., 12/04/2023, 10/11/2025)
        - DayName, MonthName DD, YYYY (e.g., Wednesday, April 12, 2023)
        - MonthName DD, YYYY (e.g., MARCH 15, 2023)
        """
        if not date_str:
            return ""
        
        date_str = date_str.strip()
        
        # Format: DD/MM/YYYY
        match = re.match(r'^(\d{1,2})/(\d{1,2})/(\d{4})$', date_str)
        if match:
            try:
                day, month, year = map(int, match.groups())
                return f"{year:04d}-{month:02d}-{day:02d}"
            except ValueError:
                pass

        # Format: MonthName DD, YYYY or Day, MonthName DD, YYYY
        # Remove day name prefix if any
        cleaned_date = re.sub(r'^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday),\s*', '', date_str, flags=re.IGNORECASE)
        # Remove extra whitespace and make title case
        cleaned_date = " ".join(cleaned_date.split())
        
        # Try parsing e.g., "April 12, 2023" or "MARCH 15, 2023"
        for fmt in ("%B %d, %Y", "%b %d, %Y", "%B %d %Y", "%b %d %Y"):
            try:
                dt = datetime.strptime(cleaned_date, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        # Try parsing lowercase month names
        try:
            # Simple manual parser for "MARCH 15, 2023" or "November 10, 2025"
            parts = re.split(r'[\s,]+', cleaned_date)
            if len(parts) >= 3:
                month_name, day_val, year_val = parts[0], parts[1], parts[2]
                months = {
                    "JAN": 1, "FEB": 2, "MAR": 3, "APR": 4, "MAY": 5, "JUN": 6,
                    "JUL": 7, "AUG": 8, "SEP": 9, "OCT": 10, "NOV": 11, "DEC": 12,
                    "JANUARY": 1, "FEBRUARY": 2, "MARCH": 3, "APRIL": 4, "JUNE": 6,
                    "JULY": 7, "AUGUST": 8, "SEPTEMBER": 9, "OCTOBER": 10, "NOVEMBER": 11, "DECEMBER": 12
                }
                m_num = months.get(month_name.upper())
                d_num = int(re.sub(r'[^\d]', '', day_val))
                y_num = int(re.sub(r'[^\d]', '', year_val))
                if m_num and d_num and y_num:
                    return f"{y_num:04d}-{m_num:02d}-{d_num:02d}"
        except Exception:
            pass

        return date_str  # Return original if unable to parse

    @classmethod
    def parse_sh7(cls, content: str) -> dict:
        """Parses Form SH-7 content and returns extracted fields."""
        data = {}
        
        # CIN & Name
        cin_match = re.search(r'Corporate Identity Number\s*\(CIN\):\s*([A-Z0-9]+)', content, re.IGNORECASE)
        data["cin"] = cin_match.group(1).strip() if cin_match else ""
        
        company_match = re.search(r'Name of the Company:\s*(.+)', content, re.IGNORECASE)
        data["company_name"] = company_match.group(1).strip() if company_match else ""

        # Resolution Date
        res_date_match = re.search(r"Date of Shareholders' Resolution:\s*([\d/]+)", content, re.IGNORECASE)
        data["shareholders_resolution_date"] = cls.normalize_date(res_date_match.group(1)) if res_date_match else ""

        # Meeting Type (AGM / EGM)
        meeting_type_match = re.search(r'Type of Meeting:\s*(.+)', content, re.IGNORECASE)
        meeting_type_str = meeting_type_match.group(1).upper() if meeting_type_match else ""
        if "AGM" in meeting_type_str or "ANNUAL" in meeting_type_str:
            data["meeting_type"] = "AGM"
        elif "EGM" in meeting_type_str or "EXTRAORDINARY" in meeting_type_str:
            data["meeting_type"] = "EGM"
        else:
            if "EXTRAORDINARY" in content.upper() or "EGM" in content.upper():
                data["meeting_type"] = "EGM"
            elif "ANNUAL" in content.upper() or "AGM" in content.upper():
                data["meeting_type"] = "AGM"
            else:
                data["meeting_type"] = "EGM"

        # Extract BEFORE and AFTER sections to avoid duplicate matches
        before_match = re.search(r'BEFORE Change:(.*?)(?:Description of Alteration|AFTER Change|Signed for|$)', content, re.DOTALL | re.IGNORECASE)
        before_section = before_match.group(1) if before_match else content

        after_match = re.search(r'AFTER Change:(.*?)(?:Signed for|$)', content, re.DOTALL | re.IGNORECASE)
        after_section = after_match.group(1) if after_match else content

        # Capital BEFORE Change
        # Equity Share Capital Before
        eq_before_match = re.search(r'Equity Share Capital:\s*([\d,]+)\s*Equity Shares of Rs\.\s*([\d,]+)[^(]*\(Total:\s*(?:Rs\.\s*)?([\d,]+)\)?', before_section, re.IGNORECASE)
        if eq_before_match:
            data["equity_shares_before"] = cls.clean_number(eq_before_match.group(1))
            data["equity_nominal_value_before"] = cls.clean_number(eq_before_match.group(2))
            data["equity_amount_before"] = cls.clean_number(eq_before_match.group(3))
        else:
            data["equity_shares_before"] = 0
            data["equity_nominal_value_before"] = 0
            data["equity_amount_before"] = 0

        # Preference Capital Before
        pref_before_match = re.search(r'Preference Share Capital:\s*([\d,]+)?\s*([a-zA-Z0-9\s]+)?of Rs\.\s*([\d,]+)?[^(]*\(Total:\s*(?:Rs\.\s*)?([\d,]+)\)?', before_section, re.IGNORECASE)
        if pref_before_match:
            data["pref_shares_before"] = cls.clean_number(pref_before_match.group(1))
            data["pref_nominal_value_before"] = cls.clean_number(pref_before_match.group(3))
            data["pref_amount_before"] = cls.clean_number(pref_before_match.group(4))
        else:
            # Fallback for NIL
            data["pref_shares_before"] = 0
            data["pref_nominal_value_before"] = 0
            data["pref_amount_before"] = 0

        total_before_match = re.search(r'Total Capital Before:\s*(?:Rs\.\s*)?([\d,]+)', before_section, re.IGNORECASE)
        data["total_capital_before"] = cls.clean_number(total_before_match.group(1)) if total_before_match else (data["equity_amount_before"] + data["pref_amount_before"])

        # Capital AFTER Change
        eq_after_match = re.search(r'Equity Share Capital:\s*([\d,]+)\s*Equity Shares of Rs\.\s*([\d,]+)[^(]*\(Total:\s*(?:Rs\.\s*)?([\d,]+)\)?', after_section, re.IGNORECASE)
        if eq_after_match:
            data["equity_shares_after"] = cls.clean_number(eq_after_match.group(1))
            data["equity_nominal_value_after"] = cls.clean_number(eq_after_match.group(2))
            data["equity_amount_after"] = cls.clean_number(eq_after_match.group(3))
        else:
            data["equity_shares_after"] = 0
            data["equity_nominal_value_after"] = 0
            data["equity_amount_after"] = 0

        pref_after_match = re.search(r'Preference Share Capital:\s*([\d,]+)\s*([a-zA-Z0-9\s\(\)]+)?of Rs\.\s*([\d,]+)?[^(]*\(Total:\s*(?:Rs\.\s*)?([\d,]+)\)?', after_section, re.IGNORECASE)
        if pref_after_match:
            data["pref_shares_after"] = cls.clean_number(pref_after_match.group(1))
            data["pref_nominal_value_after"] = cls.clean_number(pref_after_match.group(3))
            data["pref_amount_after"] = cls.clean_number(pref_after_match.group(4))
            data["pref_class_after"] = (pref_after_match.group(2) or "").strip()
        else:
            # Try a broader search for Preference Capital After
            pref_after_broad = re.search(r'Preference Share Capital:\s*([\d,]+)\s*(?:Series\s+[A-Z]\s+)?(?:CCPS|Preference\s+Shares)\s+of\s+Rs\.\s*([\d,]+)\s*\(Total:\s*(?:Rs\.\s*)?([\d,]+)\)', after_section, re.IGNORECASE)
            if pref_after_broad:
                data["pref_shares_after"] = cls.clean_number(pref_after_broad.group(1))
                data["pref_nominal_value_after"] = cls.clean_number(pref_after_broad.group(2))
                data["pref_amount_after"] = cls.clean_number(pref_after_broad.group(3))
            else:
                data["pref_shares_after"] = 0
                data["pref_nominal_value_after"] = 0
                data["pref_amount_after"] = 0
            data["pref_class_after"] = ""

        total_after_match = re.search(r'Total Capital After:\s*(?:Rs\.\s*)?([\d,]+)', content, re.IGNORECASE)
        data["total_capital_after"] = cls.clean_number(total_after_match.group(1)) if total_after_match else (data["equity_amount_after"] + data["pref_amount_after"])

        # Signatory
        signatory_name = re.search(r'Name:\s*([a-zA-Z\s]+)', content, re.IGNORECASE)
        data["signatory_name"] = signatory_name.group(1).strip() if signatory_name else ""

        signatory_din = re.search(r'DIN:\s*(\d+)', content, re.IGNORECASE)
        data["signatory_din"] = signatory_din.group(1).strip() if signatory_din else ""

        sign_date_match = re.search(r'Date of signing:\s*([\d/]+)', content, re.IGNORECASE)
        data["sign_date"] = cls.normalize_date(sign_date_match.group(1)) if sign_date_match else ""

        filing_date_match = re.search(r'Filing Date:\s*([\d/]+)', content, re.IGNORECASE)
        data["filing_date"] = cls.normalize_date(filing_date_match.group(1)) if filing_date_match else ""

        return data

    @classmethod
    def parse_board_resolution(cls, content: str) -> dict:
        """Parses Board Resolution document."""
        data = {}
        
        # Board Meeting Date
        bm_date_match = re.search(r'BOARD OF DIRECTORS.*?HELD ON\s+([A-Z0-9,\s]+?)\s+AT', content, re.IGNORECASE | re.DOTALL)
        data["board_meeting_date"] = cls.normalize_date(bm_date_match.group(1)) if bm_date_match else ""

        # Proposed EGM Convening Date
        egm_conv_match = re.search(r'Extraordinary General Meeting.*?convened on\s+([A-Z0-9,\s]+?)(?:\s+at|\s+on|\s+at\b|$)', content, re.IGNORECASE | re.DOTALL)
        data["proposed_egm_date"] = cls.normalize_date(egm_conv_match.group(1)) if egm_conv_match else ""

        # Extract DIN and Sign-off date
        din_match = re.search(r'DIN:\s*([A-Z0-9]+|\b\[PENDING[^\]]*\]\b)', content, re.IGNORECASE)
        data["signatory_din"] = din_match.group(1).strip() if din_match else ""

        date_match = re.search(r'Date:\s*([\d/]+|\b\[PENDING[^\]]*\]\b)', content, re.IGNORECASE)
        data["sign_date"] = cls.normalize_date(date_match.group(1)) if date_match and "/" in date_match.group(1) else ""

        # Detect draft indicators in resolution
        data["is_draft"] = "DRAFT" in content.upper() or "PENDING" in content.upper() or "UNSIGNED" in content.upper()

        # Share Capital Numbers from text
        # Look for "increase ... from Rs. XXX ... to Rs. YYY"
        cap_increase_match = re.search(r'increase.*?from\s+Rs\.\s*([\d,]+).*?to\s+Rs\.\s*([\d,]+)', content, re.IGNORECASE | re.DOTALL)
        if cap_increase_match:
            data["capital_before"] = cls.clean_number(cap_increase_match.group(1))
            data["capital_after"] = cls.clean_number(cap_increase_match.group(2))
        else:
            data["capital_before"] = 0
            data["capital_after"] = 0

        return data

    @classmethod
    def parse_egm_notice(cls, content: str) -> dict:
        """Parses EGM Notice document."""
        data = {}
        
        # EGM Meeting Date
        egm_date_match = re.search(r'held on\s+([A-Z0-9,\s]+?)\s+AT', content, re.IGNORECASE)
        data["egm_date"] = cls.normalize_date(egm_date_match.group(1)) if egm_date_match else ""

        # Share Capital details
        # Look for "increased from Rs. XXX ... to Rs. YYY"
        cap_increase_match = re.search(r'increased.*?from\s+Rs\.\s*([\d,]+).*?to\s+Rs\.\s*([\d,]+)', content, re.IGNORECASE | re.DOTALL)
        if cap_increase_match:
            data["capital_before"] = cls.clean_number(cap_increase_match.group(1))
            data["capital_after"] = cls.clean_number(cap_increase_match.group(2))
        else:
            data["capital_before"] = 0
            data["capital_after"] = 0

        return data

    @classmethod
    def parse_moa_clause_v(cls, content: str) -> dict:
        """Parses Memorandum of Association Clause V (Capital Clause)."""
        data = {}

        # Share Capital details
        # e.g., "The Authorised Share Capital of the Company is Rs. 50,00,000 ... divided into 5,00,000 Equity Shares"
        cap_match = re.search(r'Capital of the Company is\s+Rs\.\s*([\d,]+)[^\d]*divided into\s*([\d,]+)\s+Equity Shares', content, re.IGNORECASE)
        if cap_match:
            data["total_capital"] = cls.clean_number(cap_match.group(1))
            data["equity_shares"] = cls.clean_number(cap_match.group(2))
        else:
            # Try alternate match
            cap_match_alt = re.search(r'Capital of the Company is\s+Rs\.\s*([\d,]+)', content, re.IGNORECASE)
            data["total_capital"] = cls.clean_number(cap_match_alt.group(1)) if cap_match_alt else 0
            data["equity_shares"] = 0

        # Preference shares in MOA
        pref_match = re.search(r'([\d,]+)\s+Preference Shares', content, re.IGNORECASE)
        if pref_match:
            data["pref_shares"] = cls.clean_number(pref_match.group(1))
        else:
            pref_match_ccps = re.search(r'([\d,]+)\s+Series\s+[A-Z]\s+(?:CCPS|Preference)', content, re.IGNORECASE)
            data["pref_shares"] = cls.clean_number(pref_match_ccps.group(1)) if pref_match_ccps else 0

        # EGM date referenced
        egm_ref_match = re.search(r'held on\s*([\d/]+)', content, re.IGNORECASE)
        data["egm_date_ref"] = cls.normalize_date(egm_ref_match.group(1)) if egm_ref_match else ""

        return data

    @classmethod
    def parse_document(cls, doc_type: str, content: str) -> dict:
        """Routes to appropriate parsing function based on doc_type."""
        if doc_type == "SH_7":
            return cls.parse_sh7(content)
        elif doc_type == "BOARD_RESOLUTION":
            return cls.parse_board_resolution(content)
        elif doc_type == "EGM_NOTICE":
            return cls.parse_egm_notice(content)
        elif doc_type == "MOA_CLAUSE_V":
            return cls.parse_moa_clause_v(content)
        return {}
