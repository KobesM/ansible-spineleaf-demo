# ansible-spineleaf-demo
Demo project to configure a Spine Leaf infrastructure in GNS3 using Ansible


```
sudo docker run --rm -v $PWD:/project juniper/pyez-ansible ansible-playbook pb.conf.all.yaml -i hosts.ini
```