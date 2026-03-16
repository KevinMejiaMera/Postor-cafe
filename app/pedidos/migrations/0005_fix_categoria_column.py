from django.db import migrations


class Migration(migrations.Migration):
    """
    Esta migración soluciona el error 'column pedidos_producto.categoria_id does not exist'.
    Detecta si en la base de datos la columna todavía se llama 'categoria' y la
    renombra a 'categoria_id' para que coincida con lo que Django espera de un ForeignKey.
    """

    dependencies = [
        ('pedidos', '0004_factura_monto_recibido_factura_vuelto'),
    ]

    operations = [
        migrations.RunSQL(
            # SQL para renombrar la columna solo si existe 'categoria' y no existe 'categoria_id'
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'pedidos_producto'
                          AND column_name = 'categoria'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'pedidos_producto'
                          AND column_name = 'categoria_id'
                    ) THEN
                        ALTER TABLE pedidos_producto RENAME COLUMN categoria TO categoria_id;
                    END IF;
                END
                $$;
            """,
            # Para revertir, renombramos de vuelta si es necesario
            reverse_sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'pedidos_producto'
                          AND column_name = 'categoria_id'
                    ) AND NOT EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'pedidos_producto'
                          AND column_name = 'categoria'
                    ) THEN
                        ALTER TABLE pedidos_producto RENAME COLUMN categoria_id TO categoria;
                    END IF;
                END
                $$;
            """,
        ),
    ]
