from fastapi import APIRouter
from sqlalchemy import text

from database import engine


router = APIRouter(
    prefix="/api/v1",
    tags=["Dashboard"]
)

@router.get("/dashboard")
def get_dashboard():

    with engine.connect() as connection:

        # 1. Total suppliers
        total_suppliers_result = connection.execute(
            text("""
                SELECT COUNT(*)
                FROM suppliers;
            """)
        )

        total_suppliers = total_suppliers_result.scalar()

        # 2. Total pending
        total_pending_result = connection.execute(
            text("""
                SELECT
                    COALESCE(
                        SUM(
                            CASE
                                WHEN transaction_type = 'PURCHASE'
                                THEN amount

                                WHEN transaction_type IN (
                                    'PAYMENT',
                                    'RETURN',
                                    'CREDIT_NOTE'
                                )
                                THEN -amount

                                ELSE 0
                            END
                        ),
                        0
                    )
                FROM transactions;
            """)
        )

        total_pending = total_pending_result.scalar()

        # 3. Supplier with highest pending
        highest_pending_result = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.name,

                    COALESCE(
                        SUM(
                            CASE
                                WHEN t.transaction_type = 'PURCHASE'
                                THEN t.amount

                                WHEN t.transaction_type IN (
                                    'PAYMENT',
                                    'RETURN',
                                    'CREDIT_NOTE'
                                )
                                THEN -t.amount

                                ELSE 0
                            END
                        ),
                        0
                    ) AS pending_amount

                FROM suppliers s

                LEFT JOIN transactions t
                    ON s.id = t.supplier_id

                GROUP BY s.id, s.name

                ORDER BY pending_amount DESC

                LIMIT 1;
            """)
        )

        highest_pending = highest_pending_result.fetchone()

        # 4. Recent transactions
        recent_transactions_result = connection.execute(
            text("""
                SELECT
                    t.id,
                    t.supplier_id,
                    s.name AS supplier_name,
                    t.transaction_type,
                    t.amount,
                    t.transaction_date,
                    t.reference_number

                FROM transactions t

                JOIN suppliers s
                    ON t.supplier_id = s.id

                ORDER BY t.transaction_date DESC, t.id DESC

                LIMIT 5;
            """)
        )

        recent_transactions = []

        for row in recent_transactions_result:
            recent_transactions.append({
                "id": row.id,
                "supplier_id": row.supplier_id,
                "supplier_name": row.supplier_name,
                "transaction_type": row.transaction_type,
                "amount": float(row.amount),
                "transaction_date": str(row.transaction_date),
                "reference_number": row.reference_number
            })

    # Prepare highest pending supplier
    if highest_pending is None:
        highest_pending_supplier = None
    else:
        highest_pending_supplier = {
            "id": highest_pending.id,
            "name": highest_pending.name,
            "pending_amount": float(
                highest_pending.pending_amount
            )
        }

    return {
        "total_suppliers": total_suppliers,
        "total_pending": float(total_pending),
        "highest_pending_supplier": highest_pending_supplier,
        "recent_transactions": recent_transactions
    }