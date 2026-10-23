# Custom Inventory Implementation

This revision adds session-based custom inventory support.

- Upload a CSV with the required columns: `product_id`, `product_name`, `category`, `unit`, `current_stock`, `minimum_stock`, `target_stock`, `supplier`.
- The upload is copied into a temporary working directory for the current Streamlit session.
- Stock changes save to that working copy, not `data/sample_inventory.csv`.
- Workflow request and activity CSVs for the uploaded inventory are stored in that session work directory. The default inventory continues to use the project's existing workflow CSV files.
- Replenishment recommendations and request creation receive the active inventory path.
- This is session-based demo storage, not permanent multi-tenant storage. Temporary files may be removed when the host restarts.
- No real Orbyte API integration is included; that requires the official interface/API details.
