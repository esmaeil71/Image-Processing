FROM node:22-alpine

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Default empty: dev server proxies /api to backend (see vite.config.ts)
ARG VITE_API_URL=
ARG VITE_ORTHANC_DICOMWEB=http://localhost:8042/dicom-web

ENV VITE_API_URL=$VITE_API_URL
ENV VITE_ORTHANC_DICOMWEB=$VITE_ORTHANC_DICOMWEB

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
