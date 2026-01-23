"""
Module for ingesting sample resumes and cover letters, indexing them using FAISS,
and modifying them based on job descriptions.
"""
import os
import json
import argparse
import faiss
import numpy as np
from pathlib import Path
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from src.resume_cover_letter_generator import ResumeGenerator

# Paths for vector store and metadata
DATA_DIR = Path("../data")
INDEX_PATH = DATA_DIR / "faiss_index.idx"
META_PATH = DATA_DIR / "faiss_meta.json"

class SampleManager:
    def __init__(self):
        os.makedirs(DATA_DIR, exist_ok=True)
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        self.dim = self.embedding_model.get_sentence_embedding_dimension()
        # load or init index with ID map for vector DB
        if INDEX_PATH.exists():
            self.index = faiss.read_index(str(INDEX_PATH))
            with open(META_PATH, 'r') as f:
                self.meta: List[Dict] = json.load(f)
            # determine next id
            self.next_id = max(item['id'] for item in self.meta) + 1
        else:
            # base index and wrap in ID map
            base_index = faiss.IndexFlatL2(self.dim)
            self.index = faiss.IndexIDMap(base_index)
            self.meta = []
            self.next_id = 0

    def ingest(self, resume_path: str, cover_letter_path: str):
        # read text (docx or txt)
        def read_text(path):
            try:
                if Path(path).suffix == '.docx':
                    from docx import Document
                    doc = Document(path)
                    return '\n'.join(p.text for p in doc.paragraphs)
                else:
                    return Path(path).read_text(encoding='utf-8')
            except Exception:
                return ''
        resume_text = read_text(resume_path)
        cover_text = read_text(cover_letter_path)
        # embed combined
        text = resume_text + '\n' + cover_text
        embedding = self.embedding_model.encode(text)
        # add to FAISS vector DB with id
        vec = embedding.reshape(1, -1).astype('float32')
        self.index.add_with_ids(vec, np.array([self.next_id], dtype='int64'))
        # store metadata including vector id
        self.meta.append({"id": self.next_id, "resume": resume_path, "cover_letter": cover_letter_path})
        self.next_id += 1
        # save
        faiss.write_index(self.index, str(INDEX_PATH))
        with open(META_PATH, 'w') as f:
            json.dump(self.meta, f, indent=2)
        print(f"Ingested: {resume_path}, {cover_letter_path}")

    def modify(self, job_description: str, k: int = 2):
        # embed job description
        q_emb = self.embedding_model.encode(job_description)
        D, I = self.index.search(q_emb.reshape(1, -1).astype('float32'), k)
        generator = ResumeGenerator()
        for idx in I[0]:
            # find metadata by vector id
            meta = next(item for item in self.meta if item['id'] == int(idx))
            resume_path = meta['resume']
            cover_path = meta['cover_letter']
            resume_text = Path(resume_path).read_text(encoding='utf-8')
            cover_text = Path(cover_path).read_text(encoding='utf-8')
            # modify resume
            new_resume, _ = generator.generate_resume(
                job_description=job_description,
                candidate_profile={"text": resume_text}
            )
            # modify cover letter
            new_cover, _ = generator.generate_cover_letter(
                job_description=job_description,
                candidate_resume=resume_text,
                company_info="",
                template_type=None
            )
            print(f"Modified resume saved to: {new_resume}")
            print(f"Modified cover letter saved to: {new_cover}")

    def search_samples(self, query: str, k: int = 5) -> List[Dict]:
        """
        Search stored samples for similarity to query.
        Returns list of metadata dicts and distances.
        """
        q_emb = self.embedding_model.encode(query).reshape(1, -1).astype('float32')
        distances, ids = self.index.search(q_emb, k)
        results = []
        for dist, vid in zip(distances[0], ids[0]):
            if vid < 0:
                continue
            item = next(m for m in self.meta if m['id'] == int(vid))
            results.append({**item, 'distance': float(dist)})
        return results

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Manage sample resumes and cover letters.")
    parser.add_argument('--ingest', action='store_true', help='Ingest sample resume and cover letter')
    parser.add_argument('--resume', type=str, help='Path to sample resume')
    parser.add_argument('--cover', type=str, help='Path to sample cover letter')
    parser.add_argument('--modify', action='store_true', help='Modify samples based on job description')
    parser.add_argument('--job', type=str, help='Path to job description text file')
    args = parser.parse_args()
    manager = SampleManager()
    if args.ingest and args.resume and args.cover:
        manager.ingest(args.resume, args.cover)
    elif args.modify and args.job:
        job_desc = Path(args.job).read_text(encoding='utf-8')
        manager.modify(job_desc)
    else:
        parser.print_help()