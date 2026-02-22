
function agregarProducto(productoId) {
    // 1. Obtenemos los datos desde el contenedor oculto en el HTML
    const dataContainer = document.getElementById('data-container');
    const pedidoId = dataContainer.getAttribute('data-pedido-id');
    const csrfToken = dataContainer.getAttribute('data-csrf');
    
    const url = `/pedidos/agregar/${pedidoId}/`;

    // 2. Hacemos la petición
    fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken
        },
        body: JSON.stringify({ 'producto_id': productoId })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // Si funcionó, recargamos para actualizar la lista
            location.reload(); 
        } else {
            alert(data.message);
        }
    })
    .catch(error => console.error('Error:', error));
}