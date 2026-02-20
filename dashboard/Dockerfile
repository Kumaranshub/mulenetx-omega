FROM node:18-alpine
WORKDIR /app
RUN npm install -g serve
COPY . .
CMD ["serve","-s",".","-l","3000"]
