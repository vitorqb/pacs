FROM python:3.7-alpine

ARG VERSION

# Prepares working directory
RUN mkdir /pacs
WORKDIR /pacs

# Dependencies
RUN apk update && apk upgrade && apk add --no-cache bash tar
RUN pip install invoke

# Sends context to build
COPY dist/pacs-${VERSION}.tar.gz pacs.tar.gz
RUN tar -vzxf pacs.tar.gz && rm -rf pacs.tar.gz

# Install dependencies
RUN inv requirements

# Exposes port
EXPOSE 8000

# Set's the entrypoint
COPY docker/entrypoint entrypoint
RUN chmod +x entrypoint
ENTRYPOINT './entrypoint'
CMD []
