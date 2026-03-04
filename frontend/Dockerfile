# Build step
FROM node:18-alpine as build

WORKDIR /app
COPY package*.json ./
RUN npm install

COPY . .
# Set the React App base API URL if necessary, though proxy in package.json handles most dev things
RUN npm run build

# Serve step
FROM nginx:alpine

# Copy the built assets
COPY --from=build /app/build /usr/share/nginx/html

# Copy a custom nginx config if we needed one to route API to backend,
# but for simplicity, we can just let nginx serve the static files and expect
# the user to access API on a different port, or we can add a basic conf:
RUN echo $'server {\n\
    listen 80;\n\
    location / {\n\
    root   /usr/share/nginx/html;\n\
    index  index.html index.htm;\n\
    try_files $uri $uri/ /index.html;\n\
    }\n\
    location /api/ {\n\
    proxy_pass http://backend:8000/api/;\n\
    proxy_set_header Host $host;\n\
    proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    }' > /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
