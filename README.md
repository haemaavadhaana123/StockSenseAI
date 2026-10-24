
# StockSenseAI

StockSenseAI is an AI-assisted inventory management solution designed to help Malaysian mini-markets and small retailers improve stock visibility and replenishment decisions.

## Team Information

| Field | Details |
| :--- | :--- |
| **Team Name** | 404notFound |
| **Team Domain** | Domain 2 - Orbyte Smart SME Challenge |
| **SDG Track (1–17)** | SDG 12 — Responsible Consumption and Production |
| **Team Leader** | Haemaavadhaana Seemadaran[cite: 3] |
| **University** | Asia Pacific University of Technology and Innovation |
| **Number of Members** | 4 |


## Links

| Resource | Link |
| :--- | :--- |
| **GitHub Repository** | [https://github.com/haemaavadhaana123/StockSenseAI](https://github.com/haemaavadhaana123/StockSenseAI) |
| **Replit Project** | [https://stock-sense-ai-Haemaa.replit.app](https://stock-sense-ai-Haemaa.replit.app) |
| **Live Demo** | [ADD_YOUR_LIVE_DEMO_URL](ADD_YOUR_LIVE_DEMO_URL) |
| **Slide Deck** | [https://canva.link/lrnggdp4pdepph3)](https://canva.link/lrnggdp4pdepph3) |


## Overview

### Problem
Small and medium-sized businesses may struggle to monitor inventory levels, identify products that require replenishment, and maintain consistent purchasing workflows. Manual stock monitoring can make it harder to identify shortages promptly and keep inventory records organised. These challenges can contribute to stock shortages, unnecessary inventory, and inefficient purchasing decisions.

### Solution
StockSense AI provides a centralised dashboard for inventory monitoring and replenishment management. Built with Python and Streamlit, it processes inventory data from CSV files, identifies low-stock products using programmed rules, and calculates suggested replenishment quantities. It also supports replenishment requests, approval or rejection by a human reviewer, and activity logging. The current prototype uses rule-based inventory intelligence rather than a trained AI model, and procurement actions are simulated rather than real purchase orders.

## Key Features
* **Inventory Dashboard** — Displays inventory information and summarises stock conditions.
* **Custom Inventory Upload** — Allows businesses to upload inventory records using a CSV file.
* **Stock Monitoring** — Identifies low-stock products and products with healthy stock levels.
* **Replenishment Recommendations** — Calculates suggested order quantities based on current, minimum, and target stock levels.
* **Approval Workflow** — Supports creating, reviewing, approving, and rejecting replenishment requests.
* **Activity Log** — Records workflow activities for tracking and review.
* **SME Reusability** — Supports different businesses by accepting inventory data in a consistent CSV format.

## Tech Stack

| Layer | Technology |
| :--- | :--- |
| **Frontend / User Interface** | Streamlit |
| **Programming Language** | Python |
| **Data Processing** | pandas |
| **Data Storage** | CSV files |
| **Development Environment** | Replit |
| **Version Control** | Git and GitHub |



## Project Structure

```text
StockSenseAI/
├── app.py
├── utils/
│   ├── app_theme.py
│   ├── inventory_data.py
│   ├── workflow_storage.py
│   ├── replenishment.py
│   ├── replenishment_page.py
│   └── workflow_pages.py
├── data/
│   ├── sample_inventory.csv
│   ├── replenishment_request.csv
│   └── activity_log.csv
├── requirements.txt
└── README.md
```

## Architecture

```text
User
  │
  v
Streamlit Interface (app.py)
  │
  v
Inventory Data Processing (pandas)
  │
  v
Inventory Rules & Replenishment Logic
  │
  v
CSV-Based Storage
  │
  v
Approval Centre & Activity Log
```

# How to Run

## Option 1 — Run on Replit (Recommended)

1. Open the StockSense AI project in Replit.
2. Ensure the project files, including `app.py`, `requirements.txt`, the `utils/` directory, and the `data/` directory, are present.
3. Open the **Shell** tab in Replit.
4. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
5. Start the application:
   
  ```bash
  streamlit run app.py
  ```

## Option 2 — Run Locally

Prerequisites

* Python installed on your computer.
* Git installed if cloning the repository.
* The StockSense AI project files.

1. Clone the Repository

Replace the placeholder with your actual GitHub repository URL.
 ```bash
 git clone YOUR_GITHUB_REPOSITORY_URL
 cd StockSenseAI
  ```

If you downloaded the project files instead, open a terminal in the project directory.

2. Create a Virtual Environment

macOS / Linux
  ```bash
  python3 -m venv venv
  source venv/bin/activate
  ```

Windows
  ```bash
  python -m venv venv
  venv\Scripts\activate
  ```

3. Install Dependencies
```bash
  pip install -r requirements.txt
```

4.  Start the Application
```bash
  streamlit run app.py
```

## Using Custom Inventory Data

1. Open StockSense AI.
2. Locate Company Inventory in the sidebar.
3. Upload an inventory CSV file containing these required columns:
    * product_id
    * product_name
    * category
    * unit
    * current_stock
    * minimum_stock
    * target_stock
    * supplier
4. Review the inventory dashboard and stock conditions.
5. Open Replenishment Recommendations to view suggested order quantities.
6. Create replenishment requests and manage them through the approval workflow.

## Running Tests

If automated tests are included in the repository, run them using the appropriate test command.

For projects using Python’s built-in unittest framework with tests in a tests/ directory:

```bash
  python -m unittest discover -s tests
```


## How We Use Replit 

StockSense AI was developed and tested using Replit as its development environment.

* Development: Replit was used to write, organise, debug, and run the Python application. The project uses Streamlit to provide the inventory dashboard and workflow interface.
* Application Execution: The application is started using streamlit run app.py in the Replit Shell.
* Testing: Replit was used to test custom inventory CSV uploads, stock classification, replenishment recommendations, approval workflows, and activity logging.
* Hosting: The application runs in Replit. A publicly accessible deployment link should be provided in the Live Demo section once deployment is configured and verified.
* Secrets: No API keys or credentials should be committed to the source-code repository. No external API credentials are required for the current core inventory functionality.

📄 **Proof of Use:** [View Replit Proof of Use (PDF)](https://docs.google.com/document/d/1ZV6S-tpxHJISIzI8poKl06tY0t8hB0Bt5VE0IhShiwk/edit?usp=sharing)

## Challenges & Learnings

### Challenges Faced and How We Overcame Them

- **Inventory Data Handling:** Supporting different business inventories required a consistent CSV format. We implemented custom inventory uploads with required-column validation so users can test the application with their own inventory data.
- **Stock Classification and Replenishment:** Inventory items have different minimum and target stock levels. We implemented reusable Python logic to classify stock conditions and calculate suggested replenishment quantities.
- **Workflow Management:** Replenishment decisions require tracking and accountability. We implemented a workflow that supports request creation, approval or rejection, and activity logging.
- **Application Debugging:** During development, we encountered code and integration issues. We resolved them through debugging and repeated testing of the application's core features.

### What We Learned

- How to develop a web-based application using Python and Streamlit.
- How to process inventory records using pandas and CSV files.
- How to design reusable inventory and workflow components.
- How to implement human approval and activity logging for replenishment decisions.
- The importance of validating user-provided data and testing the application with custom inventory datasets.

## Future Improvements

- [ ] **Database Integration:** Replace CSV-based storage with a database to improve persistence, scalability, and multi-user support.
- [ ] **Orbyte Integration:** Implement and test a connection with Orbyte to support interoperability with the Orbyte ecosystem.
- [ ] **Demand Forecasting:** Introduce forecasting capabilities to estimate future inventory requirements using historical sales data.
- [ ] **Supplier Integration:** Explore supplier-system integration to streamline purchasing workflows.
- [ ] **Security and Access Control:** Add role-based permissions and stronger data protection for production use.
- [ ] **Automated Testing:** Expand automated tests for inventory validation, replenishment calculations, and workflow transitions.
- [ ] **Advanced Analytics:** Add inventory trends, usage reports, and stock movement analysis to support business decisions.

---

## Team

| Name | Role | GitHub |
|---|---|---|
| HAEMAAVDHAANA SEEMADARAN | Team Lead / Backend Developer | [@haemaavahaana123](https://github.com/haemaavadhaana123) |
| CLARANCE AMAL RAJAN | Inventory / Workflow Developer | [@clarance1214](https://github.com/claranceq214) |
| RITEIKES PRAKASH | Testing / Documentation | [@GITHUB_USERNAME](https://github.com/GITHUB_USERNAME) |
| DHARMEKA SONI  | Testing / Documentation | [@dharmeka_USERNAME](https://github.com/dharmeka) |


---

## Submission Checklist

- [ ] Team name, domain (Domain 1 / Domain 2), and SDG track completed.
- [ ] Slide deck link added, if required.
- [ ] Demo video link added, if available or required.
- [ ] Replit used and proof of use included in `submission/`.
- [ ] Preliminary submission document completed and included.
- [ ] Technical Tools Declaration completed and included.
- [ ] Submission documents renamed using the actual team name.
- [ ] GitHub repository URL added and verified.
- [ ] Live demo URL added and verified, if deployed.
- [ ] "How to Run" instructions tested.
- [ ] Custom inventory CSV upload tested.
- [ ] Replenishment request, approval/rejection, and activity logging tested.
- [ ] No API keys, passwords, or secrets committed to the repository.
- [ ] Orbyte integration status accurately described; do not claim integration until implemented and tested.

---

## License

Add the license selected by your team here.

If your repository contains a `LICENSE` file, ensure that this section names the same license. Do not claim Apache License 2.0 unless that is the license your team has actually chosen.


