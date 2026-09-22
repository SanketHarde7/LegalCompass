import re
import io
from typing import List, Tuple, Optional
import pdfplumber
import docx
from app.schemas.contract import Clause


class DocumentParser:
    """Extracts raw text and segments contracts into distinct legal clauses."""

    # Regex patterns matching standard legal section headings
    SECTION_PATTERN = re.compile(
        r"(?m)(?:"
        r"^(?:(?:Section|Clause|Article|ARTICLE|SECTION|CLAUSE)\s+[\dIVXLCDM]+[.:\s][^\n]*)|"
        r"^(?:\d{1,2}\.\s+[A-Z][^\n]*)|"
        r"^(?:[A-Z\s]{4,}(?:AGREEMENT|TERMS|INDEMNIF|TERMINATION|LIABILITY|PAYMENT|WARRANTY|CONFIDENTIAL|DISPUTE|GOVERNING|REMEDIES)[A-Z\s]*:?)"
        r")"
    )

    def __init__(self):
        self.document_title: Optional[str] = None

    def extract_from_pdf(self, file_bytes: bytes) -> Tuple[str, List[Tuple[int, str]]]:
        """Extracts text page-by-page using pdfplumber, preserving exact physical page boundaries."""
        pages_content: List[Tuple[int, str]] = []
        full_text_list: List[str] = []

        with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
            for page_idx, page in enumerate(pdf.pages, start=1):
                page_text = page.extract_text() or ""
                cleaned = self._clean_text(page_text)
                # Ensure every physical page in the PDF has an exact 1:1 representation
                pages_content.append((page_idx, cleaned))
                if cleaned.strip():
                    full_text_list.append(cleaned)

        full_text = "\n\n".join(full_text_list)
        return full_text, pages_content

    def extract_from_docx(self, file_bytes: bytes) -> Tuple[str, List[Tuple[int, str]]]:
        """Extracts text paragraph-by-paragraph using python-docx."""
        doc = docx.Document(io.BytesIO(file_bytes))
        paragraphs = [p.text for p in doc.paragraphs if p.text.strip()]
        full_text = "\n\n".join(paragraphs)
        pages_content = [(1, full_text)]
        return full_text, pages_content

    def extract_from_txt(self, file_bytes: bytes) -> Tuple[str, List[Tuple[int, str]]]:
        """Extracts text from plain text file."""
        text = file_bytes.decode("utf-8", errors="ignore")
        cleaned = self._clean_text(text)
        return cleaned, [(1, cleaned)]

    def parse_clauses(self, full_text: str, pages_content: List[Tuple[int, str]]) -> List[Clause]:
        """Segments full text into numbered clauses via regex, falling back to windowing."""
        # -------------------------------------------------------------------------
        # Root cause A: Title-exclusion step BEFORE _regex_segmentation runs.
        # Detect document title block as everything before first "RECITALS" heading or
        # first top-level numbered section match (whichever comes first).
        # Store as document_title metadata; do NOT feed it into _regex_segmentation.
        # -------------------------------------------------------------------------
        recitals_match = re.search(r"(?mi)^\s*(?:RECITALS|RECITALS:|WHEREAS)\b", full_text)
        numbered_match = re.search(
            r"(?mi)^\s*(?:(?:Section|Clause|Article|ARTICLE|SECTION|CLAUSE)\s+[\dIVXLCDM]+|\d{1,2}\.\s+[A-Z])",
            full_text,
        )

        split_indices = []
        if recitals_match:
            split_indices.append(recitals_match.start())
        if numbered_match:
            split_indices.append(numbered_match.start())

        if split_indices:
            title_boundary = min(split_indices)
            title_block = full_text[:title_boundary].strip()
            segmentable_text = full_text[title_boundary:]
        else:
            title_block = ""
            segmentable_text = full_text

        # Extract title from first meaningful line of title block
        title_lines = [l.strip() for l in title_block.splitlines() if len(l.strip()) > 3]
        self.document_title = title_lines[0] if title_lines else None

        # Pass 1: Top-level section segmentation on title-stripped text
        top_chunks = self._regex_segmentation(segmentable_text)

        # Fallback to semantic paragraph windowing if regex found fewer than 3 chunks
        if len(top_chunks) < 3:
            top_chunks = self._paragraph_windowing(segmentable_text)

        # -------------------------------------------------------------------------
        # Root cause B: Second pass _subclause_segmentation on every top-level chunk.
        # Splits chunks into sub-items (1.1, 1.2, 1.3, 1.4, etc.) inheriting parent title.
        # -------------------------------------------------------------------------
        all_chunks: List[Tuple[str, str]] = []
        for parent_heading, chunk_text in top_chunks:
            sub_clauses = self._subclause_segmentation(parent_heading, chunk_text)
            all_chunks.extend(sub_clauses)

        # -------------------------------------------------------------------------
        # Root cause C: Exact start/end character offsets relative to source page text.
        # -------------------------------------------------------------------------
        clauses: List[Clause] = []
        current_page_idx = 1
        for idx, (title, chunk_text) in enumerate(all_chunks, start=1):
            clause_id = f"clause_{idx}"
            page_num = self._find_page_number(title, chunk_text, pages_content, last_page_idx=current_page_idx)
            current_page_idx = page_num

            # Retrieve page text to determine character-exact start and end offsets
            page_text = next((pt for pidx, pt in pages_content if pidx == page_num), "")
            start_offset, end_offset = self._find_offsets_in_page(chunk_text, page_text)

            clause = Clause(
                id=clause_id,
                index=idx,
                title=title,
                text=chunk_text,
                category="OTHER",
                riskLevel="NEUTRAL",
                plainSummary="",
                suggestion=None,
                unfairnessScore=25,
                pageNumber=page_num,
                startOffset=start_offset,
                endOffset=end_offset,
            )
            clauses.append(clause)

        return clauses

    def _regex_segmentation(self, text: str) -> List[Tuple[str, str]]:
        """Splits document text using legal numbering and heading patterns."""
        matches = list(self.SECTION_PATTERN.finditer(text))
        if not matches:
            return []

        chunks: List[Tuple[str, str]] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(text)

            heading = match.group().strip()
            heading = re.sub(r"\s+", " ", heading).strip(" :.-")
            body = text[start:end].strip()

            # Root cause A Guard: If a SECTION_PATTERN match occurs within the first 300
            # characters of the text with no preceding numbered heading, treat it as noise.
            is_numbered = bool(
                re.match(
                    r"^(?:(?:Section|Clause|Article|ARTICLE|SECTION|CLAUSE)\s+[\dIVXLCDM]+|\d{1,2}\.)",
                    heading,
                    re.IGNORECASE,
                )
            )
            has_preceding_numbered = any(
                re.match(
                    r"^(?:(?:Section|Clause|Article|ARTICLE|SECTION|CLAUSE)\s+[\dIVXLCDM]+|\d{1,2}\.)",
                    m.group().strip(),
                    re.IGNORECASE,
                )
                for m in matches[:i]
            )
            if start < 300 and not is_numbered and not has_preceding_numbered:
                continue

            # Skip running headers/footers mistakenly captured as headings
            if any(
                k in heading.upper()
                for k in [
                    "STANDARD LOOPHOLE-FREE",
                    "CONFIDENTIAL & PROPRIETARY",
                    "PAGE ",
                    "AIRTIGHT COMMERCIAL MASTER SERVICES AGREEMENT",
                    "MASTER SERVICES & PROFESSIONAL",
                ]
            ):
                continue

            if len(body) > 30:  # Avoid empty micro-snippets
                chunks.append((heading, body))

        return chunks

    def _subclause_segmentation(self, parent_heading: str, chunk_text: str) -> List[Tuple[str, str]]:
        """Splits top-level section chunk into individual sub-clauses if sub-numbering is present."""
        sub_pattern = re.compile(r"(?m)^(\d{1,2}\.\d{1,3})\s+")
        matches = list(sub_pattern.finditer(chunk_text))

        if not matches:
            return [(parent_heading, chunk_text)]

        # Clean parent heading to inherit as prefix
        clean_parent = re.sub(
            r"^(?:(?:Section|Clause|Article)\s*[\dIVXLCDM]+[:.]?\s*|\d{1,2}\.\s*)",
            "",
            parent_heading,
            flags=re.IGNORECASE,
        ).strip(" :.-")

        sub_chunks: List[Tuple[str, str]] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(chunk_text)
            sub_num = match.group(1).strip()
            sub_text = chunk_text[start:end].strip()

            if len(sub_text) < 15:
                continue

            first_line = sub_text.splitlines()[0].strip()
            sub_name = self._extract_subclause_name(first_line, sub_num)

            # Inherit parent heading as prefix in title
            if sub_name:
                sub_name_lower = sub_name.lower()
                clean_parent_lower = clean_parent.lower()

                # If subclause name already includes the parent concept, don't duplicate
                if clean_parent_lower in sub_name_lower or any(
                    w in sub_name_lower for w in clean_parent_lower.split() if len(w) > 4
                ):
                    title = f"{sub_num} {sub_name}"
                elif "DEFINITIONS" in clean_parent.upper() and sub_name.startswith('"'):
                    # Any quoted term under a definitions heading: e.g. "Services", "Base Rent", "Confidential Data"
                    title = f"{sub_num} Definitions — {sub_name}"
                elif clean_parent:
                    # Check for compound parent headers (e.g. "TERM AND TERMINATION", "DEFINITIONS AND ORDER OF PRECEDENCE")
                    topics = [
                        t.strip()
                        for t in re.split(r"\s+(?:AND|&)\s+", clean_parent, flags=re.IGNORECASE)
                        if len(t.strip()) > 2
                    ]
                    matched_topic = None
                    if len(topics) > 1:
                        for topic in topics:
                            if any(w.lower() in sub_name_lower for w in topic.split() if len(w) > 3):
                                matched_topic = topic
                                break
                    
                    if matched_topic:
                        title = f"{sub_num} {matched_topic.title()} — {sub_name}"
                    elif len(clean_parent) < 35:
                        title = f"{sub_num} {clean_parent} — {sub_name}"
                    else:
                        title = f"{sub_num} {sub_name}"
                else:
                    title = f"{sub_num} {sub_name}"
            else:
                title = f"{sub_num} {clean_parent}" if clean_parent else f"Clause {sub_num}"

            sub_chunks.append((title, sub_text))

        return sub_chunks if sub_chunks else [(parent_heading, chunk_text)]

    def _extract_subclause_name(self, first_line: str, sub_num: str) -> str:
        """Extracts descriptive title from the first line of a subclause."""
        rem = re.sub(rf"^{re.escape(sub_num)}\s*", "", first_line).strip()
        if not rem:
            return ""

        # Check for quoted definition: e.g. "Services" means ...
        quote_match = re.match(r'^["\']([^"\']+)["\']', rem)
        if quote_match:
            return f'"{quote_match.group(1)}"'

        # If the first line is a clean standalone title containing an em-dash/dash (e.g. Order of Precedence — Invoicing Carve-Out)
        if any(d in rem for d in [" — ", "—", " - "]) and len(rem) <= 60:
            if not any(rem.lower().endswith(w) for w in [" means", " shall", " will", " is"]):
                return rem.strip(" .:-")

        # Check for colon delimiter: e.g. "Term: This agreement commences..."
        if ":" in rem:
            candidate = rem.split(":")[0].strip()
            if len(candidate) < 50 and len(candidate.split()) <= 6:
                return candidate

        # Check for period delimiter: e.g. "Term. This agreement commences..."
        if "." in rem:
            candidate = rem.split(".")[0].strip()
            if len(candidate) < 50 and len(candidate.split()) <= 6:
                return candidate

        # Check for dash/em-dash if line was longer than 60
        for delim in [" — ", "—", " - "]:
            if delim in rem:
                candidate = rem.split(delim)[0].strip()
                if len(candidate) < 60 and len(candidate.split()) <= 8:
                    return candidate

        # Take first 4-5 words if uppercase or title-case
        words = rem.split()
        candidate = " ".join(words[:5])
        if len(candidate) < 40:
            return candidate

        return ""

    @staticmethod
    def _normalize_with_mapping(text: str) -> Tuple[str, List[int]]:
        """Collapses whitespace and maps normalized character positions to original indices."""
        normalized_chars: List[str] = []
        norm_to_orig: List[int] = []
        in_space = False

        for orig_idx, ch in enumerate(text):
            if ch.isspace():
                if not in_space:
                    normalized_chars.append(" ")
                    norm_to_orig.append(orig_idx)
                    in_space = True
            else:
                normalized_chars.append(ch.lower())
                norm_to_orig.append(orig_idx)
                in_space = False

        return "".join(normalized_chars), norm_to_orig

    def _find_offsets_in_page(self, chunk_text: str, page_text: str) -> Tuple[Optional[int], Optional[int]]:
        """Captures character-exact start and end offsets relative to the source page text.
        
        Only accepts:
        1. Exact full substring match in page text
        2. Exact normalized full substring match with character-accurate index mapping
        
        For multi-page clauses that span across page breaks or partial matches, returns
        (None, None) to prevent bogus or fabricated partial offsets until multi-page
        sourceSpans are supported.
        """
        if not page_text or not chunk_text:
            return None, None

        # 1. Direct exact full substring match
        idx = page_text.find(chunk_text)
        if idx != -1:
            return idx, idx + len(chunk_text)

        # 2. Normalized full substring match with exact coordinate mapping
        norm_page, page_mapping = self._normalize_with_mapping(page_text)
        norm_chunk, _ = self._normalize_with_mapping(chunk_text)

        if norm_chunk and page_mapping:
            norm_idx = norm_page.find(norm_chunk)
            if norm_idx != -1 and norm_idx + len(norm_chunk) - 1 < len(page_mapping):
                orig_start = page_mapping[norm_idx]
                orig_end = page_mapping[norm_idx + len(norm_chunk) - 1] + 1
                return orig_start, min(len(page_text), orig_end)

        return None, None

    def _paragraph_windowing(self, full_text: str, target_words: int = 350) -> List[Tuple[str, str]]:
        """Fallback chunker grouping paragraphs into semantic windows."""
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        if not paragraphs:
            words = full_text.split()
            chunks = []
            for i in range(0, len(words), target_words):
                chunk_words = words[i : i + target_words]
                chunk_text = " ".join(chunk_words)
                title = f"Section {len(chunks) + 1}"
                chunks.append((title, chunk_text))
            return chunks

        chunks: List[Tuple[str, str]] = []
        current_chunk: List[str] = []
        current_word_count = 0

        for p in paragraphs:
            word_count = len(p.split())
            if current_word_count + word_count > target_words and current_chunk:
                chunk_text = "\n\n".join(current_chunk)
                first_line = current_chunk[0].split("\n")[0][:60].strip()
                title = first_line if len(first_line) > 5 else f"Section {len(chunks) + 1}"
                chunks.append((title, chunk_text))
                current_chunk = [p]
                current_word_count = word_count
            else:
                current_chunk.append(p)
                current_word_count += word_count

        if current_chunk:
            chunk_text = "\n\n".join(current_chunk)
            first_line = current_chunk[0].split("\n")[0][:60].strip()
            title = first_line if len(first_line) > 5 else f"Section {len(chunks) + 1}"
            chunks.append((title, chunk_text))

        return chunks

    def _clean_text(self, text: str) -> str:
        """Removes hyphenated line breaks and normalizes carriage returns while preserving tables & indentation."""
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        text = text.replace("(cid:127)", "•")
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
        return text.strip()

    def _find_page_number(
        self,
        title: str,
        chunk_text: str,
        pages_content: List[Tuple[int, str]],
        last_page_idx: int = 1,
    ) -> int:
        """Determines page ownership using exact text location, avoiding generic title collision."""
        if not pages_content:
            return 1

        # Generic titles that must NEVER be used for page matching alone
        GENERIC_TITLES = {"payment", "term", "liability", "confidentiality", "indemnification", "warranty", "general", "notices", "definitions", "misc"}

        # 1. Exact full chunk text in page text
        for page_idx, page_text in pages_content:
            if chunk_text in page_text:
                return page_idx

        # 2. Normalized chunk head (first 100 chars) in normalized page text
        norm_chunk, _ = self._normalize_with_mapping(chunk_text[:140])
        if len(norm_chunk) > 15:
            # Check starting from last_page_idx forward, then wrap around
            ordered_pages = sorted(pages_content, key=lambda p: (0 if p[0] >= last_page_idx else 1, p[0]))
            for page_idx, page_text in ordered_pages:
                norm_page, _ = self._normalize_with_mapping(page_text)
                if norm_chunk in norm_page:
                    return page_idx

        # 3. Distinctive first substantive line (skipping running headers)
        lines = [l.strip() for l in chunk_text.splitlines() if len(l.strip()) > 18]
        for line in lines[:3]:
            if any(k in line.upper() for k in ["CONFIDENTIAL", "PROPRIETARY", "PAGE "]):
                continue
            snip = line[:50]
            for page_idx, page_text in pages_content:
                if snip in page_text:
                    return page_idx

        # 4. Specific non-generic title keywords (only as last resort)
        clean_title = re.sub(r"^(?:(?:Section|Clause|Article)\s*[\dIVXLCDM]+[:.]?\s*|\d+\.\d+\s*)", "", title, flags=re.IGNORECASE).strip()
        if len(clean_title) > 8 and clean_title.lower() not in GENERIC_TITLES:
            for page_idx, page_text in pages_content:
                if clean_title.lower() in page_text.lower():
                    return page_idx

        return last_page_idx


document_parser = DocumentParser()
