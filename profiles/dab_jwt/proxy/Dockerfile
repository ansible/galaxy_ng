FROM golang:alpine

# hot reloads ...
RUN go install github.com/air-verse/air@latest

RUN mkdir -p /app
WORKDIR /app

CMD ["air"]
