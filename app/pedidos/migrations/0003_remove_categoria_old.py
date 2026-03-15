from django.db import migrations


class Migration(migrations.Migration):
    """
    Elimina la columna 'categoria_old' que quedó como residuo en la tabla
    pedidos_producto de la base de datos. Esta columna no existe en el modelo
    actual pero persiste en el schema de PostgreSQL causando un NOT NULL
    violation al insertar nuevos productos.
    """

    dependencies = [
        ('pedidos', '0002_initial'),
    ]

    operations = [
        migrations.RunSQL(
            # Verificamos si existe antes de eliminar (seguro en todos los entornos)
            sql="""
                DO $$
                BEGIN
                    IF EXISTS (
                        SELECT 1
                        FROM information_schema.columns
                        WHERE table_name = 'pedidos_producto'
                          AND column_name = 'categoria_old'
                    ) THEN
                        ALTER TABLE pedidos_producto DROP COLUMN categoria_old;
                    END IF;
                END
                $$;
            """,
            reverse_sql=migrations.RunSQL.noop,  # No hay vuelta atrás segura
        ),
    ]
