#  Lost and Found  

A cloud-based **Lost & Found management system** that allows users to **report, track, and recover lost items**.  
The project leverages **AWS services** for scalability, security, and reliability, with a lightweight **Flask backend** and a simple **frontend UI**.  

---

## 📌 Features  
- 📝 Report lost or found items via web interface  
- 💾 Store item details in **AWS DynamoDB**  
- 📤 Upload supporting images to **AWS S3**  
- 📢 Notify users with **AWS SNS (Simple Notification Service)**  
- 🔒 Secure access with **IAM roles & policies**  
- 🌐 Lightweight Flask backend for API endpoints  
- 📊 Export DynamoDB records as CSV for reporting  

---

## 🛠️ Tech Stack  

**Frontend**  
- HTML, CSS, JavaScript  

**Backend**  
- Python (Flask) – handles API requests  

**Cloud (AWS)** 

- **Amazon EC2** → Host frontend, backend, and admin dashboard  
- **Amazon S3** → Store images of lost and found items  
- **Amazon DynamoDB** → Store user, item, and feedback data  
- **Amazon Rekognition** → Compare item images to find a match  
- **Amazon SNS** → Send notification emails/SMS  
- **AWS IAM** → Manage permissions securely  
- **AWS Lex** → Chatbot integration


---

## 📂 Project Structure  
- Lost_and_found/
- │── Backend/                    
- │   ├── Flask.py                                  
- │── Frontend/                   
- │   ├── index.html                              
- │── Project_details/             
- │   ├── Documentation.pdf        
- │   └── Lost_and_found_application_details.csv  
- │── README.md                    


