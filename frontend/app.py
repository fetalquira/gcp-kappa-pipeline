import streamlit as st
import json
from datetime import datetime, timedelta
import pytz
from pydantic import ValidationError
import pandas as pd
import os
from shared import (
    OrderModel, 
    OrderType,
    BakeryProduct,
    PRODUCT_PRICES,
    ALLOWED_VARIANTS
)
from google.cloud import pubsub_v1
from google.oauth2 import service_account

# --- GCP CONFIG ---
# Replace with your actual Project ID from the GCP Console
PROJECT_ID = os.getenv("PROJECT_ID")
gcp_json_str = os.getenv("GOOGLE_CREDENTIALS")
TOPIC_ID = "incoming-orders"

if gcp_json_str:
    try:
        # 2. Parse the string into a Python Dictionary
        info = json.loads(gcp_json_str)
        
        # 3. Create the Credentials object directly from the dictionary
        # This is the "In-Memory" method that doesn't need a file on disk
        credentials = service_account.Credentials.from_service_account_info(info)
        
        # 4. Pass the credentials explicitly to the Publisher
        publisher = pubsub_v1.PublisherClient(credentials=credentials)
        
    except Exception as e:
        st.error(f"Failed to parse GCP credentials: {e}")
        st.stop()
else:
    st.error("GOOGLE_CREDENTIALS not found. Please provide env variable to work.")
    st.stop()

topic_path = publisher.topic_path(PROJECT_ID, TOPIC_ID)

# --- 1. INITIALIZE SESSION STATE (The Shopping Cart) ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- 2. HEADER & SETUP ---
st.set_page_config(page_title="Bakery Ordering System", layout="centered")
st.title("🥐 The Master Bakery Order Portal")
st.markdown("Submit your order below. All orders require a strict 2-day lead time.")

# --- 3. THE CART MANAGEMENT (Outside the main form) ---
st.subheader("1. Add Items to Cart")
col1, col2 = st.columns(2)
col3, col4 = st.columns(2)

with col1:
    selected_product = st.selectbox("Product", [p.value for p in BakeryProduct], index=0, help="You can only choose from our official menu.")
    product_enum_member = next(p for p in BakeryProduct if p.value == selected_product)
with col2:
    allowed_options = ALLOWED_VARIANTS.get(product_enum_member)
    selected_variant = st.selectbox("Variant/Flavor", options=allowed_options, help="Create another item on the cart if you want diff. flavors.")
with col3:
    selected_qty = st.number_input("Qty", min_value=1, step=1)
with col4:
    # AUTOMATIC PRICE LOOKUP
    # We pull the price from our shared map
    product_variants_prices = PRODUCT_PRICES.get(product_enum_member, {})
    unit_price = product_variants_prices.get(selected_variant, 0.0)
    
    # Display it in a disabled number input so the user can see it but NOT change it
    st.number_input("Unit Price (PHP)", value=unit_price, disabled=True)
    
    # Calculate Total for display
    st.caption(f"Subtotal: PHP {unit_price * selected_qty:,.2f}")

if st.button("➕ Add to Cart"):
    # Append to our session state memory
    st.session_state.cart.append({
        "product_name": selected_product,
        "variant": selected_variant if selected_variant else None,
        "quantity": selected_qty,
        "price_per_qty": unit_price
    })
    st.success(f"Added {selected_qty} x {selected_product} to cart!")

# --- 3. DISPLAY CURRENT CART ---
if st.session_state.cart:
    st.write("**🛒 Your Shopping Cart:**")
    
    # 1. Convert the list of dicts to a DataFrame
    df_cart = pd.DataFrame(st.session_state.cart)
    
    # 2. Calculate the Subtotal column
    df_cart['Subtotal'] = df_cart['quantity'] * df_cart['price_per_qty']
    
    # 3. Rename columns for the UI (Human Friendly)
    # format: "Original Key": "New Header"
    rename_map = {
        "product_name": "Product",
        "variant": "Variant/Flavor",
        "quantity": "Qty",
        "price_per_qty": "Unit Price (PHP)"
    }
    
    # We create a display version of the dataframe
    df_display = df_cart.rename(columns=rename_map)
    
    # 4. Reorder columns to make 'Subtotal' the last one
    column_order = ["Product", "Variant/Flavor", "Qty", "Unit Price (PHP)", "Subtotal"]
    df_display = df_display[column_order]

    # 5. Render the table with formatting
    st.dataframe(
        df_display.style.format({
            "Unit Price (PHP)": "₱{:,.2f}",
            "Subtotal": "₱{:,.2f}"
        }),
        width='stretch',
        hide_index=True # Hides the 0, 1, 2 row numbers
    )
    
    # 6. Show the Grand Total
    grand_total = df_cart['Subtotal'].sum()
    st.markdown(f"### **Grand Total: ₱{grand_total:,.2f}**")
    
    if st.button("🗑️ Clear Cart"):
        st.session_state.cart = []
        st.rerun()
else:
    st.info("Your cart is empty. Add items to proceed.")

st.divider()

# --- 4. DYNAMIC UI TRIGGER ---
# We put this outside the form so it dynamically shows/hides the address block
st.subheader("2. Order Details")
selected_order_type = st.radio("Delivery or Pick-up?", [OrderType.DELIVERY.value, OrderType.PICKUP.value])

# Calculate Manila Time for the Date Picker
manila_tz = pytz.timezone('Asia/Manila')
today_manila = datetime.now(manila_tz).date()
min_allowed_date = today_manila + timedelta(days=2)

# --- 5. THE CHECKOUT FORM ---
with st.form("checkout_form"):
    
    st.markdown("**Customer Information**")
    cust_name = st.text_input("Full Name")
    contact_num = st.text_input("Contact Number (e.g., 09123456789)")
    fb_name = st.text_input("Facebook Name", placeholder="Optional")
    
    # Conditional Address Block
    address_dict = None
    if selected_order_type == OrderType.DELIVERY.value:
        st.markdown("**Delivery Address**")
        addr_col1, addr_col2 = st.columns(2)
        with addr_col1:
            reg = st.text_input("Region")
            prov = st.text_input("Province")
            city = st.text_input("City")
        with addr_col2:
            brgy = st.text_input("Barangay")
            st_name = st.text_input("Street")
            unit = st.text_input("Unit/Block No.")

    st.markdown("**Schedule & Notes**")
    col_date, col_time = st.columns(2)
    with col_date:
        pref_date = st.date_input("Preferred Date", min_value=min_allowed_date)
    with col_time:
        pref_time = st.time_input("Preferred Time")
        
    notes = st.text_area("Special Instructions", placeholder="Optional")
    
    submit_button = st.form_submit_button("Submit Order")

# --- 6. PYDANTIC VALIDATION & EXECUTION ---
if submit_button:
    if not st.session_state.cart:
        st.error("❌ You cannot submit an empty cart.")
    else:
        # Build the address dictionary ONLY if delivery was selected
        if selected_order_type == OrderType.DELIVERY.value:
            address_dict = {
                "region": reg, "province": prov, "city": city,
                "barangay": brgy, "street": st_name,
                "unit_no": unit if unit else None
            }

        # Construct the raw data dictionary from the form inputs
        raw_payload = {
            "customer_name": cust_name,
            "contact_number": contact_num,
            "facebook_name": fb_name if fb_name else None,
            "order_type": selected_order_type,
            "address": address_dict,
            "items": st.session_state.cart,
            "preferred_date": pref_date,
            "preferred_time": pref_time,
            "notes": notes if notes else None
        }

        # THE GATEKEEPER: Pass raw data to Pydantic
        try:
            # If this line succeeds, the data is 100% clean and valid.
            validated_order = OrderModel(**raw_payload)
            
            # 1. Convert our Pydantic object to a JSON string, then to Bytes
            # Pub/Sub only sends bytes, not Python objects!
            data_bytes = validated_order.model_dump_json().encode("utf-8")
            
            # 2. Publish to the Cloud
            # We add an attribute 'origin' for filtering later
            future = publisher.publish(topic_path, data=data_bytes, origin="streamlit-app")
            
            # 3. Wait for the confirmation from GCP
            message_id = future.result() 
            
            st.success(f"✅ Order confirmed! Transaction ID: {validated_order.transaction_id}")
            
            # Clear the cart after successful submission
            st.session_state.cart = []
            
        except ValidationError as e:
            # If Pydantic catches an error (e.g., bad phone number), we display it gracefully.
            st.error("❌ Validation Failed. Please fix the following errors:")
            for error in e.errors():
                # Extract which field failed and the error message
                field = " -> ".join([str(loc) for loc in error["loc"]])
                msg = error["msg"]
                st.warning(f"**{field}**: {msg}")

        except Exception as e:
            st.error(f"⚠️ Failed to send order to Cloud: {e}")