FROM golang:alpine

# hot reloads ...
RUN go install github.com/cosmtrek/air@latest

RUN mkdir -p /app
WORKDIR /app

CMD ["air"]
