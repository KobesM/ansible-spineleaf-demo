# ansible-spineleaf-demo
Demo project to configure a Spine Leaf infrastructure in GNS3 using Ansible


```
sudo ansible-playbook -i hosts.ini pb.check.netconf.yaml
```

```
sudo docker run --rm -v $PWD:/project juniper/pyez-ansible ansible-playbook pb.conf.all.yaml -i hosts.ini
```