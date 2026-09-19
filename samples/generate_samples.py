import os
import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont


def create_sample_files(output_dir: str = "samples"):
    os.makedirs(output_dir, exist_ok=True)

    # 1. Clean Digital PDF
    pdf1_path = os.path.join(output_dir, "clean_digital.pdf")
    doc1 = fitz.open()
    page1 = doc1.new_page()
    text_content1 = """COMPUTER NETWORKS & DISTRIBUTED SYSTEMS EXAM
Duration: 3 Hours                                  Max Marks: 100

1. Which of the following transport layer protocols provides reliable, ordered, and error-checked delivery of a stream of octets?
A. UDP
B. TCP
C. IP
D. ICMP

2. What is the standard port number used by HTTPS communication?
(a) 80
(b) 443
(c) 8080
(d) 22

3. In the context of database transactions, what does ACID stand for?
A. Atomicity, Consistency, Isolation, Durability
B. Accuracy, Concurrency, Integrity, Durability
C. Availability, Consistency, Isolation, Distribution
D. Atomicity, Concurrency, Isolation, Dependability

4. Explain the difference between synchronous and asynchronous message passing in distributed architectures.

Answer Key:
1. B
2. B
3. A
"""
    page1.insert_text((50, 60), text_content1, fontsize=11)
    doc1.save(pdf1_path)
    doc1.close()

    # 2. Multi-Page Question PDF
    pdf2_path = os.path.join(output_dir, "multipage_question.pdf")
    doc2 = fitz.open()
    # Page 1
    p1 = doc2.new_page()
    p1_text = """DISTRIBUTED SYSTEMS MIDTERM - PART A
Page 1 of 2

1. Which algorithm is widely used for leader election in distributed consensus?
A. Paxos
B. Dijkstra
C. Bellman-Ford
D. Floyd-Warshall

2. Consider a distributed key-value store operating under the CAP theorem. During a network partition event, if the system chooses to remain available to client read and write requests, which of the following trade-offs must it accept?
A. Strong immediate consistency will be sacrificed for eventual consistency.
B. Latency will decrease to zero across all partitions.
"""
    p1.insert_text((50, 60), p1_text, fontsize=11)

    # Page 2 (Continuation of Question 2 + Question 3)
    p2 = doc2.new_page()
    p2_text = """DISTRIBUTED SYSTEMS MIDTERM - PART B
Page 2 of 2

C. The system will reject all subsequent write requests permanently.
D. Data will be duplicated across all nodes instantaneously.

3. State True or False: In a purely peer-to-peer network, there is no centralized coordinator or server.
A. True
B. False

Answer Key:
1. A
2. A
3. A
"""
    p2.insert_text((50, 60), p2_text, fontsize=11)
    doc2.save(pdf2_path)
    doc2.close()

    # 3. Separate Answer Key PDF
    pdf3_path = os.path.join(output_dir, "separate_answer_key.pdf")
    doc3 = fitz.open()
    p3 = doc3.new_page()
    p3_text = """OFFICIAL EXAMINATION SOLUTIONS & ANSWER KEYS
Course: CS-401 Computer Networks

Answer Key:
1 - B
2 - B
3 - A
4 - Descriptive
"""
    p3.insert_text((50, 60), p3_text, fontsize=12)
    doc3.save(pdf3_path)
    doc3.close()

    # 4. Standalone Sample PNG Image
    img_path = os.path.join(output_dir, "sample_question.png")
    img = Image.new("RGB", (800, 300), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    img_text = """1. Which sorting algorithm has an average time complexity of O(n log n)?
A. QuickSort
B. BubbleSort
C. InsertionSort
D. SelectionSort"""
    d.text((30, 40), img_text, fill=(0, 0, 0))
    img.save(img_path)

    # 5. Invalid text file
    txt_path = os.path.join(output_dir, "invalid_file.txt")
    with open(txt_path, "w") as f:
        f.write("This is a plain text file not allowed for document processing.")

    print("Sample test documents created successfully in 'samples/' directory.")


if __name__ == "__main__":
    create_sample_files()
