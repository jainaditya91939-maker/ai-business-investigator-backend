from fastapi import APIRouter, HTTPException

from sqlalchemy import text

from database import engine

from schemas import TransactionCreate


router = APIRouter(
    prefix="/api/v1",
    tags=["Transactions"]
)


@router.post("/transactions")
def create_transaction(transaction: TransactionCreate):

    with engine.begin() as connection:

        # Check whether supplier exists
        supplier_result = connection.execute(
            text("""
                SELECT id
                FROM suppliers
                WHERE id = :supplier_id;
            """),
            {
                "supplier_id": transaction.supplier_id
            }
        )

        supplier = supplier_result.fetchone()

        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found"
            )

        # Check for duplicate transaction
        duplicate_result = connection.execute(
            text("""
                SELECT id
                FROM transactions
                WHERE supplier_id = :supplier_id
                AND transaction_type = :transaction_type
                AND amount = :amount
                AND transaction_date = :transaction_date
                AND (
                    reference_number = :reference_number
                    OR (
                        reference_number IS NULL
                        AND :reference_number IS NULL
                    )
                );
            """),
            {
                "supplier_id": transaction.supplier_id,
                "transaction_type": transaction.transaction_type,
                "amount": transaction.amount,
                "transaction_date": transaction.transaction_date,
                "reference_number": transaction.reference_number
            }
        )

        duplicate_transaction = duplicate_result.fetchone()

        if duplicate_transaction is not None:
            raise HTTPException(
                status_code=409,
                detail="Duplicate transaction detected"
            )

        # Insert transaction
        result = connection.execute(
            text("""
                INSERT INTO transactions (
                    supplier_id,
                    transaction_type,
                    amount,
                    transaction_date,
                    reference_number,
                    notes
                )
                VALUES (
                    :supplier_id,
                    :transaction_type,
                    :amount,
                    :transaction_date,
                    :reference_number,
                    :notes
                )
                RETURNING
                    id,
                    supplier_id,
                    transaction_type,
                    amount,
                    transaction_date,
                    reference_number,
                    notes;
            """),
            {
                "supplier_id": transaction.supplier_id,
                "transaction_type": transaction.transaction_type,
                "amount": transaction.amount,
                "transaction_date": transaction.transaction_date,
                "reference_number": transaction.reference_number,
                "notes": transaction.notes
            }
        )

        new_transaction = result.fetchone()

    return {
        "message": "Transaction created successfully",
        "transaction": {
            "id": new_transaction.id,
            "supplier_id": new_transaction.supplier_id,
            "transaction_type": new_transaction.transaction_type,
            "amount": float(new_transaction.amount),
            "transaction_date": str(new_transaction.transaction_date),
            "reference_number": new_transaction.reference_number,
            "notes": new_transaction.notes
        }
    }

@router.get("/transactions")
def get_transactions():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    t.id,
                    t.supplier_id,
                    s.name AS supplier_name,
                    t.transaction_type,
                    t.amount,
                    t.transaction_date,
                    t.reference_number,
                    t.notes,
                    t.created_at
                FROM transactions t
                JOIN suppliers s
                    ON s.id = t.supplier_id
                ORDER BY
                    t.transaction_date DESC,
                    t.id DESC;
            """)
        )

        transactions = result.fetchall()

    return [
        {
            "id": transaction.id,
            "supplier_id": transaction.supplier_id,
            "supplier_name": transaction.supplier_name,
            "transaction_type": transaction.transaction_type,
            "amount": float(transaction.amount),
            "transaction_date": str(
                transaction.transaction_date
            ),
            "reference_number": transaction.reference_number,
            "notes": transaction.notes,
            "created_at": str(transaction.created_at),
        }
        for transaction in transactions
    ]