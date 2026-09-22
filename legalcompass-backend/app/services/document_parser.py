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
        raw_chunks = self._regex_segmentation(full_text)

        # Fallback to semantic paragraph windowing if regex found fewer than 3 chunks
        if len(raw_chunks) < 3:
            raw_chunks = self._paragraph_windowing(full_text)

        clauses: List[Clause] = []
        for idx, (title, chunk_text) in enumerate(raw_chunks, start=1):
            clause_id = f"clause_{idx}"
            page_num = self._find_page_number(title, chunk_text, pages_content)
            
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
            )
            clauses.append(clause)

        return clauses

    def _regex_segmentation(self, full_text: str) -> List[Tuple[str, str]]:
        """Splits document text using legal numbering and heading patterns."""
        matches = list(self.SECTION_PATTERN.finditer(full_text))
        if not matches:
            return []

        chunks: List[Tuple[str, str]] = []
        for i, match in enumerate(matches):
            start = match.start()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(full_text)
            
            heading = match.group().strip()
            # Clean heading
            heading = re.sub(r"\s+", " ", heading).strip(" :.-")
            body = full_text[start:end].strip()

            # Skip running headers/footers mistakenly captured as headings
            if any(k in heading.upper() for k in [
                "STANDARD LOOPHOLE-FREE",
                "CONFIDENTIAL & PROPRIETARY",
                "PAGE ",
                "AIRTIGHT COMMERCIAL MASTER SERVICES AGREEMENT",
                "MASTER SERVICES & PROFESSIONAL",
            ]):
                continue

            if len(body) > 30:  # Avoid empty micro-snippets
                chunks.append((heading, body))

        return chunks

    def _paragraph_windowing(self, full_text: str, target_words: int = 350) -> List[Tuple[str, str]]:
        """Fallback chunker grouping paragraphs into semantic windows."""
        paragraphs = [p.strip() for p in full_text.split("\n\n") if p.strip()]
        if not paragraphs:
            # Simple word-level chunking
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
        # Replace non-printable cid bullets from PDFs with clean bullets
        text = text.replace("(cid:127)", "•")
        # Fix hyphenated words broken across lines: e.g. "obliga-\ntion" -> "obligation"
        text = re.sub(r"(\w+)-\n(\w+)", r"\1\2", text)
        return text.strip()

    def _find_page_number(self, title: str, chunk_text: str, pages_content: List[Tuple[int, str]]) -> int:
        """Maps a clause snippet back to its source PDF page number accurately."""
        # 1. Try finding by distinctive title keywords
        clean_title = re.sub(r"^(SECTION|Clause|Article)\s*[\dIVXLCDM]+[:.]?\s*", "", title, flags=re.IGNORECASE).strip()
        if len(clean_title) > 6:
            for page_idx, page_text in pages_content:
                if clean_title.lower() in page_text.lower():
                    return page_idx

        # 2. Try finding by distinctive body lines (skipping header tokens)
        lines = [l.strip() for l in chunk_text.splitlines() if len(l.strip()) > 20]
        for line in lines[:4]:
            if any(k in line.upper() for k in ["AIRTIGHT COMMERCIAL", "STANDARD LOOPHOLE", "CONFIDENTIAL & PROPRIETARY", "PAGE "]):
                continue
            snip = line[:60]
            for page_idx, page_text in pages_content:
                if snip in page_text:
                    return page_idx

        return 1


document_parser = DocumentParser()
