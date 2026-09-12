from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine
from schemas import SupplierCreate


router = APIRouter(
    prefix="/api/v1",
    tags=["Suppliers"]
)


# GET ALL SUPPLIERS
@router.get("/suppliers")
def get_suppliers():
    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    phone,
                    address,
                    created_at
                FROM suppliers
                ORDER BY id;
            """)
        )

        suppliers = []

        for row in result:
            suppliers.append({
                "id": row.id,
                "name": row.name,
                "phone": row.phone,
                "address": row.address,
                "created_at": str(row.created_at)
            })

    return suppliers


# CREATE SUPPLIER
@router.post("/suppliers")
def create_supplier(supplier: SupplierCreate):

    with engine.begin() as connection:

        # Check for duplicate supplier
        duplicate_result = connection.execute(
            text("""
                SELECT id
                FROM suppliers
                WHERE LOWER(TRIM(name)) = LOWER(TRIM(:name))
                AND (
                    phone = :phone
                    OR (
                        phone IS NULL
                        AND :phone IS NULL
                    )
                );
            """),
            {
                "name": supplier.name,
                "phone": supplier.phone
            }
        )

        duplicate_supplier = duplicate_result.fetchone()

        if duplicate_supplier is not None:
            raise HTTPException(
                status_code=409,
                detail="Duplicate supplier detected"
            )

        # Insert supplier
        result = connection.execute(
            text("""
                INSERT INTO suppliers (
                    name,
                    phone,
                    address
                )
                VALUES (
                    :name,
                    :phone,
                    :address
                )
                RETURNING
                    id,
                    name,
                    phone,
                    address,
                    created_at;
            """),
            {
                "name": supplier.name.strip(),
                "phone": supplier.phone.strip()
                    if supplier.phone
                    else None,
                "address": supplier.address.strip()
                    if supplier.address
                    else None
            }
        )

        new_supplier = result.fetchone()

    return {
        "message": "Supplier created successfully",
        "supplier": {
            "id": new_supplier.id,
            "name": new_supplier.name,
            "phone": new_supplier.phone,
            "address": new_supplier.address,
            "created_at": str(new_supplier.created_at)
        }
    }


# SUPPLIER SUMMARY
@router.get("/suppliers/summary")
def get_suppliers_summary():

    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    s.id,
                    s.name,
                    s.phone,
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
                GROUP BY
                    s.id,
                    s.name,
                    s.phone
                ORDER BY
                    pending_amount DESC,
                    s.id;
            """)
        )

        suppliers = []

        for row in result:
            suppliers.append({
                "id": row.id,
                "name": row.name,
                "phone": row.phone,
                "pending_amount": float(
                    row.pending_amount
                )
            })

    return suppliers


# SUPPLIER BALANCE
@router.get("/suppliers/{supplier_id}/balance")
def get_supplier_balance(supplier_id: int):

    with engine.connect() as connection:

        # Check whether supplier exists
        supplier_result = connection.execute(
            text("""
                SELECT
                    id,
                    name
                FROM suppliers
                WHERE id = :supplier_id;
            """),
            {
                "supplier_id": supplier_id
            }
        )

        supplier = supplier_result.fetchone()

        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found"
            )

        # Calculate pending balance
        balance_result = connection.execute(
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
                    ) AS pending_amount
                FROM transactions
                WHERE supplier_id = :supplier_id;
            """),
            {
                "supplier_id": supplier_id
            }
        )

        pending_amount = balance_result.scalar()

    return {
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "pending_amount": float(
            pending_amount
        )
    }


# SUPPLIER LEDGER
@router.get("/suppliers/{supplier_id}/ledger")
def get_supplier_ledger(supplier_id: int):

    with engine.connect() as connection:

        # Check whether supplier exists
        supplier_result = connection.execute(
            text("""
                SELECT
                    id,
                    name
                FROM suppliers
                WHERE id = :supplier_id;
            """),
            {
                "supplier_id": supplier_id
            }
        )

        supplier = supplier_result.fetchone()

        if supplier is None:
            raise HTTPException(
                status_code=404,
                detail="Supplier not found"
            )

        # Get supplier ledger
        result = connection.execute(
            text("""
                SELECT
                    id,
                    transaction_date,
                    transaction_type,
                    reference_number,
                    notes,

                    CASE
                        WHEN transaction_type = 'PURCHASE'
                            THEN amount
                        ELSE 0
                    END AS debit,

                    CASE
                        WHEN transaction_type IN (
                            'PAYMENT',
                            'RETURN',
                            'CREDIT_NOTE'
                        )
                            THEN amount
                        ELSE 0
                    END AS credit,

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
                    ) OVER (
                        ORDER BY transaction_date, id
                    ) AS running_balance

                FROM transactions

                WHERE supplier_id = :supplier_id

                ORDER BY
                    transaction_date,
                    id;
            """),
            {
                "supplier_id": supplier_id
            }
        )

        ledger = []

        for row in result:
            ledger.append({
                "id": row.id,
                "transaction_date": str(
                    row.transaction_date
                ),
                "transaction_type": row.transaction_type,
                "reference_number": row.reference_number,
                "notes": row.notes,
                "debit": float(row.debit),
                "credit": float(row.credit),
                "running_balance": float(
                    row.running_balance
                )
            })

    return {
        "supplier_id": supplier.id,
        "supplier_name": supplier.name,
        "ledger": ledger
    }


# GET SINGLE SUPPLIER
@router.get("/suppliers/{supplier_id}")
def get_supplier(supplier_id: int):

    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    id,
                    name,
                    phone,
                    address,
                    created_at
                FROM suppliers
                WHERE id = :supplier_id;
            """),
            {
                "supplier_id": supplier_id
            }
        )

        supplier = result.fetchone()

    if supplier is None:
        raise HTTPException(
            status_code=404,
            detail="Supplier not found"
        )

    return {
        "id": supplier.id,
        "name": supplier.name,
        "phone": supplier.phone,
        "address": supplier.address,
        "created_at": str(
            supplier.created_at
        )
    }