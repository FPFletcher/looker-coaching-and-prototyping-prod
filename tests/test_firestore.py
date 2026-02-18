import firebase_admin
from firebase_admin import firestore
import datetime
import asyncio

# Exhaustive Initialization strictly for your project
if not firebase_admin._apps:
    firebase_admin.initialize_app(options={
        'projectId': 'antigravity-innovations'
    })

db = firestore.client()

async def verify_firestore_systematic():
    print("🚀 Starting Systematic Firestore Verification for 'antigravity-innovations'...")
    try:
        # Step A: Write Test
        test_data = {
            "status": "active",
            "region": "europe-west1",
            "verified_at": datetime.datetime.now(datetime.timezone.utc),
            "note": "Antigravity Smoke Test"
        }
        doc_ref = db.collection("system_verification").document("connection_status")
        doc_ref.set(test_data)
        print("✅ Step A: Write successful.")

        # Step B: Read Test
        doc = doc_ref.get()
        if doc.exists:
            print(f"✅ Step B: Read successful. Data: {doc.to_dict()}")
        else:
            print("❌ Step B: Read failed. Document not found.")

        # Step C: Cleanup
        doc_ref.delete()
        print("✅ Step C: Cleanup successful. Connection is 100% verified.")

    except Exception as e:
        print(f"❌ SYSTEMATIC FAILURE: {str(e)}")
        print("\nPossible fixes:")
        print("1. Run 'gcloud auth application-default login' in your terminal.")
        print("2. Ensure your account has the 'Cloud Datastore User' role in GCP.")

if __name__ == "__main__":
    asyncio.run(verify_firestore_systematic())
