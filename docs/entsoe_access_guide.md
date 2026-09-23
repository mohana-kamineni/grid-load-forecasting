# ENTSO-E Transparency Platform Access Guide

This guide describes how to obtain and configure access to the **ENTSO-E Transparency Platform** for Project P4.

---

## 1. Programmatic Access via REST API (Recommended)

The ENTSO-E Transparency Platform provides a public REST API under Regulation (EU) No 543/2013.

### Step 1: Create an Account
1. Visit the [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/).
2. Click **Login / Register** in the top-right corner.
3. Complete the free user registration using a valid email address and confirm your email.

### Step 2: Request REST API Access
1. Send an email to **`transparency@entsoe.eu`**.
2. **Subject line:** `RESTful API access`
3. **Body:** State that you are requesting API access for academic / research purposes (grid-load forecasting study).
4. Typical turnaround is within 1–3 business days.

### Step 3: Generate Security Token
1. Once your account has been granted API access, log in to the platform.
2. Navigate to **My Account** -> **Security Token**.
3. Click **Generate** (or copy your existing token).

### Step 4: Configure Project Credentials
1. In the root of `p4-grid-load-forecasting`, copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```
2. Set the `ENTSOE_API_KEY` variable:
   ```env
   ENTSOE_API_KEY=your_actual_security_token_here
   ```
   > [!CAUTION]
   > Never commit `.env` or paste your token into public issues/commits. `.gitignore` is configured to exclude all `.env` files.

---

## 2. Alternative Access: Direct Web Portal / File Library Export

If REST API access approval is delayed, ENTSO-E provides manual export capabilities directly through its web portal:

### Method A: Data Portal Export
1. Navigate to: `Data` -> `Load` -> `Actual Total Load [6.1.A]`.
2. Set **Country / Bidding Zone:** `Sweden (SE3)` (EIC: `10Y1001A1001A46L`).
3. Set Date Range: `2022-01-01` to `2025-12-31`.
4. Click **Export** -> **CSV**.
5. Repeat for `Day-ahead Total Load Forecast [6.1.B]`.
6. Save exported CSV files into: `data/raw/`.

### Method B: File Library (Bulk Downloads)
1. Navigate to: `Data` -> `File Library`.
2. Browse to `Actual Total Load` and `Day-Ahead Total Load Forecast`.
3. Download the relevant annual/monthly packages for SE3 (2022–2025).
4. Place files into `data/raw/`.

---

## 3. Strict Verification & Ingestion Protocols

* The ingestion module (`src/data/ingest.py`) will automatically verify file headers, EIC area codes, process types, and timestamps against official schema standards.
* The API client (`src/data/client.py`) will explicitly distinguish between:
  - **HTTP 401/403 Authentication Failures:** Invalid or missing token.
  - **HTTP 400 Bad Request:** Rejected query parameter.
  - **HTTP 200 with Empty Body / No TimeSeries:** Data not published for the requested period.
* An empty API response will **never** be treated as valid data or a Gate 0 pass.
