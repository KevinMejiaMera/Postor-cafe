
from django.test import TestCase
from .models import Mesa, Producto, Pedido
from usuarios.models import Usuario

class PedidosModelTest(TestCase):

    def setUp(self):
       
        # 1. Creamos una mesa de prueba
        self.mesa = Mesa.objects.create(
            numero=99, 
            capacidad=4, 
            estado='libre'
        )
        
        # 2. Creamos un producto de prueba
        self.hamburguesa = Producto.objects.create(
            nombre="Hamburguesa Test",
            precio=5.50,
            stock=10,
            disponible=True
        )

    def test_creacion_mesa(self):
        """Prueba que la mesa se guardó correctamente"""
        mesa_guardada = Mesa.objects.get(numero=99)
        self.assertEqual(mesa_guardada.capacidad, 4)
        self.assertEqual(mesa_guardada.estado, 'libre')
        print("\n✅ Test de Mesa: OK")

    def test_stock_producto(self):
        """Prueba que el producto tiene el stock correcto"""
        producto = Producto.objects.get(nombre="Hamburguesa Test")
        self.assertEqual(producto.stock, 10)
        self.assertEqual(float(producto.precio), 5.50)
        print("✅ Test de Producto: OK")

    def test_cambio_estado_mesa(self):
        """Prueba que podemos cambiar el estado de la mesa"""
        self.mesa.estado = 'ocupada'
        self.mesa.save()
        
        # Volvemos a leer de la base de datos
        mesa_actualizada = Mesa.objects.get(numero=99)
        self.assertEqual(mesa_actualizada.estado, 'ocupada')
        print("✅ Test de Estado de Mesa: OK")