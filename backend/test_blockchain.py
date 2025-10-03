from services.blockchain_service import create_invoice_on_chain, approve_invoice_on_chain, get_blockchain_status

print("🧪 Testing CloudCred Blockchain Integration")
print("=" * 50)

# Test 1: Check connection
print("1. Testing connection...")
status = get_blockchain_status()
print(f"✅ Connected: {status['connected']}")
print(f"✅ Balance: {status['balance']}")

# Test 2: Create invoice on blockchain
print("\n2. Creating test invoice on blockchain...")
result = create_invoice_on_chain(
    invoice_id="TEST_001",
    freelancer_email="john@freelancer.com",
    client_email="sarah@client.com", 
    amount=0.1,  # 0.1 ETH
    description="Test invoice for CloudCred blockchain integration"
)

print(f"Invoice creation result: {result}")

if result['success']:
    print("✅ Invoice successfully created on blockchain!")
    
    # Test 3: Approve the invoice
    print("\n3. Approving invoice on blockchain...")
    approval_result = approve_invoice_on_chain("TEST_001", "client_123")
    
    print(f"Approval result: {approval_result}")
    
    if approval_result['success']:
        print("✅ Invoice successfully approved on blockchain!")
        print("🎉 Full blockchain integration working!")
    else:
        print("❌ Invoice approval failed")
else:
    print("❌ Invoice creation failed")

print("\n" + "=" * 50)
print("🏁 Test complete!")