// 장바구니를 저장할 배열
let cart = [];

// 장바구니에 상품 추가 함수
function addToCart(productName, price) {
    // 상품이 이미 장바구니에 있다면 수량을 증가
    let found = false;
    for (let item of cart) {
        if (item.name === productName) {
            item.quantity += 1;
            found = true;
            break;
        }
    }

    // 장바구니에 없다면 새 항목으로 추가
    if (!found) {
        cart.push({
            name: productName,
            price: price,
            quantity: 1
        });
    }

    // 장바구니 업데이트
    updateCart();
}

// 장바구니에서 상품 삭제 함수
function removeFromCart(index) {
    cart.splice(index, 1);
    updateCart();
}

// 장바구니 목록 업데이트 함수
function updateCart() {
    const cartList = document.getElementById('cart-list');
    cartList.innerHTML = ''; // 기존 항목 지우기

    for (let i = 0; i < cart.length; i++) {
        const item = cart[i];
        const li = document.createElement('li');
        li.textContent = `${item.name} - ${item.price * item.quantity}원 (수량: ${item.quantity})`;

        // 수량 조정 버튼 추가
        const plusButton = document.createElement('button');
        plusButton.textContent = '+';
        plusButton.onclick = () => {
            item.quantity += 1;
            updateCart();
        };

        const minusButton = document.createElement('button');
        minusButton.textContent = '-';
        minusButton.onclick = () => {
            if (item.quantity > 1) {
                item.quantity -= 1;
            } else {
                removeFromCart(i);
            }
            updateCart();
        };

        // 버튼 추가
        li.appendChild(plusButton);
        li.appendChild(minusButton);
        cartList.appendChild(li);
    }
}

// "장바구니에 담기" 버튼 클릭 이벤트
const addButtons = document.querySelectorAll('.add-to-cart');
addButtons.forEach(button => {
    button.addEventListener('click', (event) => {
        const productName = event.target.getAttribute('data-product');
        const price = parseInt(event.target.getAttribute('data-price'), 10);
        addToCart(productName, price);
    });
});

// 주문하기 버튼 클릭 이벤트
document.getElementById('order-button').addEventListener('click', () => {
    window.location.href = "https://sites.google.com/view/robloxbuy1/%ED%99%88?read_current=1";  // 주문 페이지로 리디렉션
});
