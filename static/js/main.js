document.addEventListener('DOMContentLoaded', function() {
    // Функция для добавления билета в корзину
    window.addToCart = function(eventId) {
        const formData = new URLSearchParams();
        formData.append('action', 'add_to_cart');
        formData.append('event_id', eventId);

        fetch('/cgi-bin/index.cgi', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json; charset=UTF-8'
            },
            body: formData.toString()
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.success) {
                alert(data.message);
                window.location.href = '/cgi-bin/index.cgi?action=cart';
            } else {
                if (data.error === 'Необходима авторизация') {
                    window.location.href = '/cgi-bin/index.cgi?action=login';
                } else {
                    alert(data.error || 'Ошибка при добавлении билета в корзину');
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при добавлении в корзину');
        });
    };

    // Функция для удаления билета из корзины
    window.removeFromCart = function(eventId) {
        if (confirm('Вы уверены, что хотите удалить этот билет из корзины?')) {
            const formData = new URLSearchParams();
            formData.append('action', 'remove_from_cart');
            formData.append('event_id', eventId);

            fetch('/cgi-bin/index.cgi', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                    'Accept': 'application/json; charset=UTF-8'
                },
                body: formData.toString()
            })
            .then(response => {
                if (response.redirected) {
                    window.location.href = response.url;
                } else {
                    location.reload();
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('Произошла ошибка при удалении из корзины');
            });
        }
    };

    // Функция для обновления статуса заказа (для менеджера)
    window.updateOrderStatus = function(orderId, newStatus) {
        const formData = new URLSearchParams();
        formData.append('action', 'update_order_status');
        formData.append('order_id', orderId);
        formData.append('status', newStatus);

        fetch('/cgi-bin/index.cgi', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'Accept': 'application/json; charset=UTF-8'
            },
            body: formData.toString()
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
            } else {
                location.reload();
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при обновлении статуса');
        });
    };
}); 