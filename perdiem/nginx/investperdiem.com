server {
    server_name investperdiem.com;
    return 301 https://www.investperdiem.com$request_uri;
}

server {
    server_name www.investperdiem.com;

    access_log off;
    client_max_body_size 50M;

    location / {
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $http_host;

        if ($http_x_forwarded_proto != "https") {
            rewrite ^(.*)$ https://$server_name$1 permanent;
        }

        proxy_pass http://127.0.0.1:8000;
        add_header P3P 'CP="ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV"';
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains;";
    }
}

server {
    listen 80 default_server;
    server_name _;

    access_log off;

    location /health-check {
        proxy_set_header X-Forwarded-Host $server_name;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header Host $http_host;

        proxy_pass http://127.0.0.1:8000;
        add_header P3P 'CP="ALL DSP COR PSAa PSDa OUR NOR ONL UNI COM NAV"';
    }
}
