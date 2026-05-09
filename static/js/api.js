const api = {
    async request(endpoint, options = {}) {
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json'
            }
        };

        const response = await fetch(endpoint, {
            ...defaultOptions,
            ...options,
            headers: {
                ...defaultOptions.headers,
                ...(options.headers || {})
            }
        });

        if (response.status === 204) {
            return null;
        }

        const data = await response.json().catch(() => ({}));

        if (!response.ok) {
            const message = data.detail || `Request failed with status ${response.status}`;
            throw new Error(message);
        }

        return data;
    },

    async login(credentials) {
        return this.request('/api/login', {
            method: 'POST',
            body: JSON.stringify(credentials)
        });
    },

    async listApplications() {
        return this.request('/api/applications');
    },

    async createApplication(application) {
        return this.request('/api/applications', {
            method: 'POST',
            body: JSON.stringify(application)
        });
    },

    async updateApplication(id, updates) {
        return this.request(`/api/applications/${id}`, {
            method: 'PATCH',
            body: JSON.stringify(updates)
        });
    },

    async updateApplicationStatus(id, newStatus) {
        return this.updateApplication(id, { status: newStatus });
    },

    async deleteApplication(id) {
        return this.request(`/api/applications/${id}`, {
            method: 'DELETE'
        });
    }
};

window.api = api;
