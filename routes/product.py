from fastapi import APIRouter, HTTPException
from sqlalchemy import text

from database import engine
from schemas import ProductCreate


router = APIRouter(
    prefix="/api/v1",
    tags=["Products"]
)


# CREATE PRODUCT
@router.post("/products")
def create_product(product: ProductCreate):

    with engine.begin() as connection:

        # Check supplier if supplier_id is provided
        if product.supplier_id is not None:
            supplier_result = connection.execute(
                text("""
                    SELECT id
                    FROM suppliers
                    WHERE id = :supplier_id;
                """),
                {
                    "supplier_id": product.supplier_id
                }
            )

            supplier = supplier_result.fetchone()

            if supplier is None:
                raise HTTPException(
                    status_code=404,
                    detail="Supplier not found"
                )

        # Check duplicate product
        duplicate_result = connection.execute(
            text("""
                SELECT id
                FROM products
                WHERE LOWER(TRIM(name)) =
                      LOWER(TRIM(:name))
                AND (
                    supplier_id = :supplier_id
                    OR (
                        supplier_id IS NULL
                        AND :supplier_id IS NULL
                    )
                );
            """),
            {
                "name": product.name,
                "supplier_id": product.supplier_id
            }
        )

        duplicate_product = duplicate_result.fetchone()

        if duplicate_product is not None:
            raise HTTPException(
                status_code=409,
                detail="Duplicate product detected for this supplier"
            )

        # Insert product
        result = connection.execute(
            text("""
                INSERT INTO products (
                    name,
                    category,
                    supplier_id,
                    price,
                    stock
                )
                VALUES (
                    :name,
                    :category,
                    :supplier_id,
                    :price,
                    :stock
                )
                RETURNING
                    id,
                    name,
                    category,
                    supplier_id,
                    price,
                    stock,
                    created_at;
            """),
            {
                "name": product.name.strip(),
                "category": (
                    product.category.strip()
                    if product.category
                    else None
                ),
                "supplier_id": product.supplier_id,
                "price": product.price,
                "stock": product.stock
            }
        )

        new_product = result.fetchone()

    return {
        "message": "Product created successfully",
        "product": {
            "id": new_product.id,
            "name": new_product.name,
            "category": new_product.category,
            "supplier_id": new_product.supplier_id,
            "price": float(new_product.price),
            "stock": new_product.stock,
            "created_at": str(
                new_product.created_at
            )
        }
    }


# GET ALL PRODUCTS
@router.get("/products")
def get_products():

    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    p.id,
                    p.name,
                    p.category,
                    p.supplier_id,
                    s.name AS supplier_name,
                    p.price,
                    p.stock,
                    p.created_at
                FROM products p
                LEFT JOIN suppliers s
                    ON p.supplier_id = s.id
                ORDER BY p.id DESC;
            """)
        )

        products = result.fetchall()

    return [
        {
            "id": product.id,
            "name": product.name,
            "category": product.category,
            "supplier_id": product.supplier_id,
            "supplier_name": product.supplier_name,
            "price": float(product.price),
            "stock": product.stock,
            "created_at": str(
                product.created_at
            )
        }
        for product in products
    ]


# GET SINGLE PRODUCT
@router.get("/products/{product_id}")
def get_product(product_id: int):

    with engine.connect() as connection:
        result = connection.execute(
            text("""
                SELECT
                    p.id,
                    p.name,
                    p.category,
                    p.supplier_id,
                    s.name AS supplier_name,
                    p.price,
                    p.stock,
                    p.created_at
                FROM products p
                LEFT JOIN suppliers s
                    ON p.supplier_id = s.id
                WHERE p.id = :product_id;
            """),
            {
                "product_id": product_id
            }
        )

        product = result.fetchone()

    if product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "id": product.id,
        "name": product.name,
        "category": product.category,
        "supplier_id": product.supplier_id,
        "supplier_name": product.supplier_name,
        "price": float(product.price),
        "stock": product.stock,
        "created_at": str(
            product.created_at
        )
    }


# UPDATE PRODUCT
@router.put("/products/{product_id}")
def update_product(
    product_id: int,
    product: ProductCreate
):

    with engine.begin() as connection:

        # Check product exists
        existing_product = connection.execute(
            text("""
                SELECT id
                FROM products
                WHERE id = :product_id;
            """),
            {
                "product_id": product_id
            }
        ).fetchone()

        if existing_product is None:
            raise HTTPException(
                status_code=404,
                detail="Product not found"
            )

        # Check supplier if provided
        if product.supplier_id is not None:
            supplier = connection.execute(
                text("""
                    SELECT id
                    FROM suppliers
                    WHERE id = :supplier_id;
                """),
                {
                    "supplier_id": product.supplier_id
                }
            ).fetchone()

            if supplier is None:
                raise HTTPException(
                    status_code=404,
                    detail="Supplier not found"
                )

        # Check duplicate product during update
        duplicate_product = connection.execute(
            text("""
                SELECT id
                FROM products
                WHERE LOWER(TRIM(name)) =
                      LOWER(TRIM(:name))
                AND (
                    supplier_id = :supplier_id
                    OR (
                        supplier_id IS NULL
                        AND :supplier_id IS NULL
                    )
                )
                AND id != :product_id;
            """),
            {
                "name": product.name,
                "supplier_id": product.supplier_id,
                "product_id": product_id
            }
        ).fetchone()

        if duplicate_product is not None:
            raise HTTPException(
                status_code=409,
                detail="Duplicate product detected for this supplier"
            )

        # Update product
        result = connection.execute(
            text("""
                UPDATE products
                SET
                    name = :name,
                    category = :category,
                    supplier_id = :supplier_id,
                    price = :price,
                    stock = :stock
                WHERE id = :product_id
                RETURNING
                    id,
                    name,
                    category,
                    supplier_id,
                    price,
                    stock,
                    created_at;
            """),
            {
                "product_id": product_id,
                "name": product.name.strip(),
                "category": (
                    product.category.strip()
                    if product.category
                    else None
                ),
                "supplier_id": product.supplier_id,
                "price": product.price,
                "stock": product.stock
            }
        )

        updated_product = result.fetchone()

    return {
        "message": "Product updated successfully",
        "product": {
            "id": updated_product.id,
            "name": updated_product.name,
            "category": updated_product.category,
            "supplier_id": updated_product.supplier_id,
            "price": float(updated_product.price),
            "stock": updated_product.stock,
            "created_at": str(
                updated_product.created_at
            )
        }
    }


# DELETE PRODUCT
@router.delete("/products/{product_id}")
def delete_product(product_id: int):

    with engine.begin() as connection:
        result = connection.execute(
            text("""
                DELETE FROM products
                WHERE id = :product_id
                RETURNING id;
            """),
            {
                "product_id": product_id
            }
        )

        deleted_product = result.fetchone()

    if deleted_product is None:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return {
        "message": "Product deleted successfully",
        "product_id": deleted_product.id
    }