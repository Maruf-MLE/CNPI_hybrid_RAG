\# RAG Project Development Instructions



তোমার কাজ হলো আমার RAG Project-এর development, planning এবং implementation-এ সহায়তা করা।



\## 1. Source of Truth (সবচেয়ে গুরুত্বপূর্ণ)



সবসময় `plan` folder-কে Source of Truth হিসেবে গণ্য করবে  tobe plan e kono vul thakle seta songe songe bola..emon kono jaiga jeita kaj korbe na sei jaiga ta bola,,ar emon kono kichu kora jabe na jeta asole kaj korbe na sejonnno ege dekhe sure hoye niye kaj soro korba।



কোনো feature, flow, architecture, node, state, data flow বা implementation করার আগে নিচের file-gুলো review করবে:



1\. `README.md`

2\. Architecture JSON file

3\. Diagram HTML file (যদি README বা JSON থেকে পরিষ্কারভাবে না বোঝা যায়)

4\. `state.py`

5.'work phase'



Priority Order:



README.md → JSON Diagram → HTML Diagram → state.py - work phase.txt



কোনো conflict পাওয়া গেলে নিজে সিদ্ধান্ত নেবে না। আমাকে জানাবে।



\---



\## 2. Architecture Compliance



Project-এর architecture, flow, node connection, routing logic এবং state management অবশ্যই plan folder-এর design অনুসরণ করবে।



নিজের ইচ্ছামতো flow পরিবর্তন করবে না।



বিশেষভাবে focus করবে:



\* Query Flow

\* Node Routing

\* State Update Flow

\* RAG Pipeline

\* Error Handling Flow

\* Parallel Execution Flow

\* Data Movement Between Nodes



\---



\## 3. State Management Rules



Project-এর State Schema অবশ্যই `state.py` অনুযায়ী হবে।



\* State variable-এর নাম পরিবর্তন করবে না।

\* অপ্রয়োজনীয় state add করবে না।

\* State structure modify করার আগে আমাকে জানাবে।

\* State flow সবসময় architecture-এর সাথে consistent রাখতে হবে।



\---



\## 4. Clarification First



কোনো requirement, node, flow, algorithm, state field বা architecture বুঝতে সমস্যা হলে:



\* অনুমান করবে না।

\* নিজে সিদ্ধান্ত নেবে না।

\* Implementation শুরু করার আগে আমাকে প্রশ্ন করবে।



Rule:



"Never guess critical architecture decisions."



\---



\## 5. Code Quality Standards



সব code হবে:



\* Clean

\* Readable

\* Maintainable

\* Modular

\* Scalable

\* Production-ready



Follow:



\* SOLID principles

\* DRY (Don't Repeat Yourself)

\* Single Responsibility Principle

\* Proper naming conventions

\* Type hints যেখানে সম্ভব

\* Clear comments only where necessary



\---



\## 6. Performance Requirements



সবসময় low latency এবং high efficiency মাথায় রেখে design করবে।



Focus Areas:



\* Minimize unnecessary LLM calls

\* Minimize database queries

\* Efficient retrieval strategy

\* Efficient state updates

\* Reduce redundant processing

\* Optimize response time



যদি কোনো performance bottleneck দেখো, আমাকে জানাবে।



\---



\## 7. Algorithm Selection



Algorithm, retrieval strategy বা ranking technique বাছাই করার সময়:



\* Accuracy

\* Scalability

\* Cost

\* Latency

\* Maintainability



এই বিষয়গুলো বিবেচনা করবে।



যদি কোনো better alternative থাকে, suggest করতে পারো।



\---



\## 8. Development Process



প্রতিবার কোনো code লেখার আগে:



1\. Requirement analyze করবে

2\. Architecture verify করবে

3\. Flow verify করবে

4\. State impact check করবে

5\. তারপর implementation করবে



Code দেওয়ার সময় জানাবে:



\* কী implement করলে

\* কেন করলে

\* কোন flow follow করলে

\* State-এর উপর কী impact পড়বে

\* Future consideration কী



\---



\## 9. Problem Detection



Architecture, diagram, state design বা flow-এর মধ্যে কোনো সমস্যা, inconsistency, ambiguity বা scalability issue দেখলে:



\* আমাকে জানাবে

\* কারণ ব্যাখ্যা করবে

\* Possible solution suggest করবে



\---



\## 10. Long-Term Maintainability



Code এমনভাবে লিখবে যাতে:



\* বারবার refactor করতে না হয়

\* Future feature add করা সহজ হয়

\* Debugging সহজ হয়

\* Testing সহজ হয়



প্রয়োজনে implementation-এর আগে design improvement suggest করতে পারো।



\---



\## Final Rule



Plan Folder-এর design, diagram এবং state structure-ই চূড়ান্ত reference।



কোনো critical decision নেওয়ার আগে verification করবে।



যদি নিশ্চিত না হও, প্রশ্ন করবে।

Guess করবে না।



