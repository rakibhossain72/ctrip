// This is a conceptual example of a plugin for an e-commerce platform.

class CtripPaymentGateway {
    constructor(apiKey) {
        this.apiKey = apiKey;
        this.apiUrl = 'http://localhost:8080'; // Replace with your actual API URL
    }

    async createPayment(amount) {
        const response = await fetch(`${this.apiUrl}/generate_payment_address`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-Api-Key': this.apiKey,
            },
            body: JSON.stringify({ amount }),
        });
        return response.json();
    }

    async checkPaymentStatus(paymentAddress) {
        const response = await fetch(`${this.apiUrl}/check_payment/${paymentAddress}`);
        return response.json();
    }
}

// Example usage within an e-commerce checkout flow:
async function handleCheckout(amount) {
    const gateway = new CtripPaymentGateway('testapi');
    const paymentDetails = await gateway.createPayment(amount);

    if (paymentDetails.payment_address) {
        console.log(`Please send your payment to: ${paymentDetails.payment_address}`);

        // Poll for payment confirmation
        const interval = setInterval(async () => {
            const status = await gateway.checkPaymentStatus(paymentDetails.payment_address);
            if (status.status === '1') {
                console.log('Payment confirmed!');
                clearInterval(interval);
                // Proceed with order fulfillment
            }
        }, 10000); // Check every 10 seconds
    } else {
        console.error('Failed to create payment address.');
    }
}

// handleCheckout(100); // Example call
