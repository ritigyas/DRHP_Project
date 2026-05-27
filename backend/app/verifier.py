import os

class DocumentVerifier:
    EVENT_TITLES = {
        "Event1": "Seed Funding Capital Increase (FY 2023-24)",
        "Event2": "Series A Funding and CCPS Introduction (FY 2024-25)",
        "Event3": "Series B Funding & Preference Reclassification (FY 2025-26)"
    }

    @classmethod
    def verify_event(cls, event_id: str, documents: dict) -> dict:
        """
        Cross-references files for a single corporate event/package and returns the results.
        `documents` is a dict mapping doc_type (e.g. "SH_7", "BOARD_RESOLUTION") to its parsed data dict and metadata.
        Each entry in `documents` looks like:
        {
            "content": str,
            "filename": str,
            "classification": { "document_type": str, "filing_status": str, "event_id": str },
            "parsed_data": dict
        }
        """
        logs = []
        anomalies = []
        status = "Confirmed"

        sh7 = documents.get("SH_7")
        br = documents.get("BOARD_RESOLUTION")
        egm = documents.get("EGM_NOTICE")
        moa = documents.get("MOA_CLAUSE_V")

        # --- Check 1: Document Completeness ---
        required_types = ["SH_7", "BOARD_RESOLUTION", "EGM_NOTICE", "MOA_CLAUSE_V"]
        for t in required_types:
            present = t in documents
            label = f"Document Presence: {t.replace('_', ' ').title()}"
            if present:
                logs.append({"label": label, "status": "PASS", "message": f"Document is present ({documents[t]['filename']})."})
            else:
                logs.append({"label": label, "status": "FAIL", "message": f"[UNVERIFIED — source not found] Missing supporting {t.replace('_', ' ').title()} document."})
                anomalies.append(f"Missing supporting {t.replace('_', ' ').title()} document.")
                status = "Flagged"

        # If SH_7 is missing, we cannot establish the baseline of the event
        if not sh7:
            return {
                "event_id": event_id,
                "title": cls.EVENT_TITLES.get(event_id, f"Corporate Event - {event_id}"),
                "sh7_filing_date": "[UNVERIFIED — source not found]",
                "egm_date": "[UNVERIFIED — source not found]",
                "total_capital_before": 0,
                "total_capital_after": 0,
                "equity_shares_after": 0,
                "pref_shares_after": 0,
                "status": "Flagged",
                "verification_logs": logs,
                "anomalies": anomalies + ["Cannot compile table row: Form SH-7 is missing."],
                "documents_metadata": {k: {"filename": v["filename"], "status": v["classification"]["filing_status"]} for k, v in documents.items()}
            }

        sh7_data = sh7["parsed_data"]

        # --- Check 2: Unsigned/Draft Document warnings ---
        for t, doc in documents.items():
            doc_status = doc["classification"]["filing_status"]
            label = f"Filing Status: {t.replace('_', ' ').title()}"
            if doc_status == "DRAFT":
                logs.append({
                    "label": label,
                    "status": "WARN",
                    "message": f"[UNVERIFIED — draft document] {doc['filename']} is an unsigned draft."
                })
                anomalies.append(f"{t.replace('_', ' ').title()} is a Draft (Unsigned).")
                status = "Flagged"
            else:
                logs.append({"label": label, "status": "PASS", "message": f"{t.replace('_', ' ').title()} is official and signed."})

        # --- Check 3: Date Cross-Referencing ---
        # A. Shareholders Resolution Date vs EGM Notice Date
        sh7_egm_date = sh7_data.get("shareholders_resolution_date")
        if egm:
            egm_data = egm["parsed_data"]
            egm_date = egm_data.get("egm_date")
            label = "EGM Date Verification"
            if not sh7_egm_date or not egm_date:
                logs.append({"label": label, "status": "FAIL", "message": "[UNVERIFIED — date missing] EGM Date could not be extracted from both documents."})
                anomalies.append("EGM Date missing in filings.")
                status = "Flagged"
            elif sh7_egm_date == egm_date:
                logs.append({"label": label, "status": "PASS", "message": f"EGM Date matches perfectly between SH-7 and EGM Notice ({sh7_egm_date})."})
            else:
                logs.append({
                    "label": label,
                    "status": "FAIL",
                    "message": f"[UNVERIFIED — source mismatch] Date mismatch. Form SH-7 says {sh7_egm_date}, EGM Notice says {egm_date}."
                })
                anomalies.append(f"EGM Date mismatch: SH-7 states {sh7_egm_date} while EGM Notice states {egm_date}.")
                status = "Flagged"
        else:
            logs.append({"label": "EGM Date Verification", "status": "FAIL", "message": "[UNVERIFIED — source not found] Cannot verify EGM date; EGM Notice is missing."})

        # B. Board Resolution Proposed EGM Date vs EGM Notice Date
        if br:
            br_data = br["parsed_data"]
            proposed_egm_date = br_data.get("proposed_egm_date")
            label = "Board Resolution EGM Date Convene"
            if proposed_egm_date:
                target_date = sh7_egm_date or (egm_data.get("egm_date") if egm else "")
                if proposed_egm_date == target_date:
                    logs.append({"label": label, "status": "PASS", "message": f"Board resolution convened EGM for correct date ({proposed_egm_date})."})
                else:
                    logs.append({
                        "label": label,
                        "status": "FAIL",
                        "message": f"[UNVERIFIED — source mismatch] Convene date mismatch. Board Resolution convened EGM for {proposed_egm_date}, EGM resolved on {target_date}."
                    })
                    anomalies.append(f"Board Resolution proposed EGM on {proposed_egm_date}, EGM was actually held on {target_date}.")
                    status = "Flagged"
            else:
                logs.append({"label": label, "status": "WARN", "message": "EGM convene date not parsed from Board Resolution."})

            # Check that Board Meeting Date is BEFORE EGM Date
            bm_date = br_data.get("board_meeting_date")
            if bm_date and sh7_egm_date:
                label = "Board Meeting Sequence"
                if bm_date < sh7_egm_date:
                    logs.append({"label": label, "status": "PASS", "message": f"Board meeting held on {bm_date}, before EGM on {sh7_egm_date}."})
                else:
                    logs.append({
                        "label": label,
                        "status": "FAIL",
                        "message": f"[UNVERIFIED — logic mismatch] Timeline error. Board meeting held on {bm_date}, which is on/after EGM date {sh7_egm_date}."
                    })
                    anomalies.append(f"Chronological error: Board meeting date ({bm_date}) is not before EGM date ({sh7_egm_date}).")
                    status = "Flagged"

        # C. MOA Clause V EGM date ref vs EGM Date
        if moa:
            moa_data = moa["parsed_data"]
            moa_egm_ref = moa_data.get("egm_date_ref")
            label = "MOA EGM Date Reference"
            if moa_egm_ref:
                target_date = sh7_egm_date or (egm_data.get("egm_date") if egm else "")
                if moa_egm_ref == target_date:
                    logs.append({"label": label, "status": "PASS", "message": f"MOA amendment reference date matches EGM ({moa_egm_ref})."})
                else:
                    logs.append({
                        "label": label,
                        "status": "FAIL",
                        "message": f"[UNVERIFIED — source mismatch] MOA reference mismatch. MOA points to meeting on {moa_egm_ref}, EGM held on {target_date}."
                    })
                    anomalies.append(f"MOA references EGM date {moa_egm_ref}, while EGM date in SH-7 is {target_date}.")
                    status = "Flagged"
            else:
                logs.append({"label": label, "status": "WARN", "message": "No EGM date reference parsed from MOA clause."})

        # --- Check 4: Capital Calculations & Value Cross-Referencing ---
        # A. Self-consistency of SH-7
        eq_before = sh7_data.get("equity_amount_before", 0)
        pref_before = sh7_data.get("pref_amount_before", 0)
        total_before = sh7_data.get("total_capital_before", 0)
        
        eq_after = sh7_data.get("equity_amount_after", 0)
        pref_after = sh7_data.get("pref_amount_after", 0)
        total_after = sh7_data.get("total_capital_after", 0)

        label = "SH-7 Mathematical Integrity"
        if (eq_before + pref_before == total_before) and (eq_after + pref_after == total_after):
            logs.append({"label": label, "status": "PASS", "message": f"Capital sums match before ({total_before:,}) and after ({total_after:,})."})
        else:
            logs.append({
                "label": label,
                "status": "FAIL",
                "message": f"[UNVERIFIED — math mismatch] Sub-components do not add up to total capital. Before: {eq_before:,} eq + {pref_before:,} pref = {total_before:,}. After: {eq_after:,} eq + {pref_after:,} pref = {total_after:,}."
            })
            anomalies.append("Form SH-7 has arithmetic inconsistency in share capital sums.")
            status = "Flagged"

        # B. Cross-reference SH-7 Capital After with Board Resolution
        if br:
            br_data = br["parsed_data"]
            br_cap_after = br_data.get("capital_after", 0)
            label = "Board Resolution Capital Match"
            if br_cap_after == 0:
                logs.append({"label": label, "status": "WARN", "message": "Capital after change could not be parsed from Board Resolution."})
            elif br_cap_after == total_after:
                logs.append({"label": label, "status": "PASS", "message": f"Board resolution capital matches SH-7 ({total_after:,})."})
            else:
                logs.append({
                    "label": label,
                    "status": "FAIL",
                    "message": f"[UNVERIFIED — source mismatch] Board resolution capital ({br_cap_after:,}) does not match SH-7 ({total_after:,})."
                })
                anomalies.append(f"Board Resolution capital of Rs. {br_cap_after:,} mismatches SH-7 capital of Rs. {total_after:,}.")
                status = "Flagged"

        # C. Cross-reference SH-7 Capital After with EGM Notice
        if egm:
            egm_data = egm["parsed_data"]
            egm_cap_after = egm_data.get("capital_after", 0)
            label = "EGM Notice Capital Match"
            if egm_cap_after == 0:
                logs.append({"label": label, "status": "WARN", "message": "Capital after change could not be parsed from EGM Notice."})
            elif egm_cap_after == total_after:
                logs.append({"label": label, "status": "PASS", "message": f"EGM notice capital matches SH-7 ({total_after:,})."})
            else:
                logs.append({
                    "label": label,
                    "status": "FAIL",
                    "message": f"[UNVERIFIED — source mismatch] EGM notice capital ({egm_cap_after:,}) does not match SH-7 ({total_after:,})."
                })
                anomalies.append(f"EGM Notice capital of Rs. {egm_cap_after:,} mismatches SH-7 capital of Rs. {total_after:,}.")
                status = "Flagged"

        # D. Cross-reference SH-7 Capital After with MOA Clause V
        if moa:
            moa_data = moa["parsed_data"]
            moa_total = moa_data.get("total_capital", 0)
            moa_eq_shares = moa_data.get("equity_shares", 0)
            moa_pref_shares = moa_data.get("pref_shares", 0)
            
            label = "MOA Capital Clause V Match"
            
            sh7_eq_shares = sh7_data.get("equity_shares_after", 0)
            sh7_pref_shares = sh7_data.get("pref_shares_after", 0)

            mismatch_reasons = []
            if moa_total != total_after:
                mismatch_reasons.append(f"Total Capital (MOA: {moa_total:,} vs SH-7: {total_after:,})")
            if moa_eq_shares != sh7_eq_shares and moa_eq_shares > 0:
                mismatch_reasons.append(f"Equity Shares (MOA: {moa_eq_shares:,} vs SH-7: {sh7_eq_shares:,})")
            if moa_pref_shares != sh7_pref_shares:
                mismatch_reasons.append(f"Preference Shares (MOA: {moa_pref_shares:,} vs SH-7: {sh7_pref_shares:,})")

            if not mismatch_reasons:
                logs.append({"label": label, "status": "PASS", "message": f"MOA Clause V capital matches SH-7 perfectly ({total_after:,})."})
            else:
                reason_str = ", ".join(mismatch_reasons)
                logs.append({
                    "label": label,
                    "status": "FAIL",
                    "message": f"[UNVERIFIED — source mismatch] MOA Clause V values mismatch Form SH-7: {reason_str}."
                })
                anomalies.append(f"MOA Clause V mismatch: {reason_str}.")
                status = "Flagged"

        return {
            "event_id": event_id,
            "title": cls.EVENT_TITLES.get(event_id, f"Corporate Event - {event_id}"),
            "sh7_filing_date": sh7_data.get("filing_date", ""),
            "egm_date": sh7_egm_date,
            "meeting_type": sh7_data.get("meeting_type", "EGM"),
            "total_capital_before": total_before,
            "total_capital_after": total_after,
            "equity_shares_after": sh7_data.get("equity_shares_after", 0),
            "pref_shares_after": sh7_data.get("pref_shares_after", 0),
            "pref_class_after": sh7_data.get("pref_class_after", "NIL"),
            "status": status,
            "verification_logs": logs,
            "anomalies": anomalies,
            "documents_metadata": {k: {"filename": v["filename"], "status": v["classification"]["filing_status"]} for k, v in documents.items()}
        }
