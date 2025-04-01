document.addEventListener('DOMContentLoaded', function() {
    // Функция для добавления билета в корзину
    window.addToCart = function(eventId, quantity, zoneId) {
        // Validate inputs
        if (!eventId || !quantity) {
            showError('Ошибка: отсутствуют обязательные параметры');
            return;
        }

        // Create form data
        const formData = new FormData();
        formData.append('action', 'add_to_cart');
        formData.append('event_id', eventId);
        formData.append('quantity', quantity);
        
        // If zoneId is provided, add it to form data
        if (zoneId) {
            formData.append('zone_id', zoneId);
        } else {
            // If no zoneId, redirect to zone selection page
            window.location.href = `/cgi-bin/index.cgi?action=select_zone&event_id=${eventId}&quantity=${quantity}`;
            return;
        }

        // Send request
        fetch('/cgi-bin/index.cgi', {
            method: 'POST',
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                showSuccess(data.message);
                // Update cart count if needed
                updateCartCount();
            } else {
                showError(data.error || 'Произошла ошибка при добавлении в корзину');
                if (data.debug) {
                    console.error('Debug info:', data.debug);
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
            showError('Произошла ошибка при отправке запроса');
        });
    }

    function showSuccess(message) {
        const notification = document.createElement('div');
        notification.className = 'notification success';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    function showError(message) {
        const notification = document.createElement('div');
        notification.className = 'notification error';
        notification.textContent = message;
        document.body.appendChild(notification);
        
        setTimeout(() => {
            notification.remove();
        }, 3000);
    }

    function updateCartCount() {
        // This function can be implemented to update the cart count in the header
        // For now, we'll just refresh the page to show the updated cart
        window.location.reload();
    }

    // Add styles for notifications
    const style = document.createElement('style');
    style.textContent = `
        .notification {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 25px;
            border-radius: 4px;
            color: white;
            font-weight: bold;
            z-index: 1000;
            animation: slideIn 0.3s ease-out;
        }
        
        .notification.success {
            background-color: #28a745;
        }
        
        .notification.error {
            background-color: #dc3545;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(100%);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    document.head.appendChild(style);

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

    // Функция для оформления заказа
    window.checkout = function() {
        const formData = new URLSearchParams();
        formData.append('action', 'checkout');

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
            window.location.href = '/cgi-bin/index.cgi?action=cart';
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Произошла ошибка при оформлении заказа');
        });
    };
}); 