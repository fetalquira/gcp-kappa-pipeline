import streamlit as st
import json
from datetime import datetime, timedelta
import pytz
from pydantic import ValidationError

# Import your Data Contract
# Note: Adjust the import path based on your folder structure (e.g., from shared.schemas import ...)
from shared import OrderModel, OrderItem, Address, OrderType, BakeryProduct

# --- 1. INITIALIZE SESSION STATE (The Shopping Cart) ---
if "cart" not in st.session_state:
    st.session_state.cart = []

# --- 2. HEADER & SETUP ---
st.set_page_config(page_title="Bakery Ordering System", layout="centered")
st.title("🥐 The Master Bakery Order Portal")
st.markdown("Submit your order below. All orders require a strict 2-day lead time.")

# --- 3. THE CART MANAGEMENT (Outside the main form) ---
st.subheader("1. Add Items to Cart")
col1, col2, col3, col4 = st.columns(4)

with col1:
    selected_product = st.selectbox("Product", [p.value for p in BakeryProduct])
with col2:
    selected_variant = st.text_input("Variant (e.g., Cheese)", placeholder="Optional")
with col3:
    selected_qty = st.number_input("Qty", min_value=1, step=1)
with col4:
    selected_price = st.number_input("Price (PHP)", min_value=0.0, step=50.0)

if st.button("➕ Add to Cart"):
    # Append to our session state memory
    st.session_state.cart.append({
        "product_name": selected_product,
        "variant": selected_variant if selected_variant else None,
        "quantity": selected_qty,
        "price_per_qty": selected_price
    })
    st.success(f"Added {selected_qty}x {selected_product} to cart!")

# Display current cart
if st.session_state.cart:
    st.write("**Current Cart:**")
    st.dataframe(st.session_state.cart)
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
            unit = st.text_input("Unit/Block No.", placeholder="Optional")

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
            
            # Print the clean JSON to the terminal (Mocking the Pub/Sub publish)
            st.success("✅ Order Validated Successfully! Check your terminal for the JSON payload.")
            print("\n--- NEW VALIDATED ORDER PAYLOAD ---")
            print(validated_order.model_dump_json(indent=2))
            print("-----------------------------------\n")
            
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