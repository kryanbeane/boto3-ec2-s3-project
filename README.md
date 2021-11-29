# Automatic EC2 & S3 Bucket Launch Program

Launches an S3 bucket and EC2 Instance with Apache web server with little to no user input.

## Description

Developer Operations assignment 1 worth 40% of the module for Semester 5. Program which launches an EC2 instance with an Apache web server installed with instance meta data on the index.html page. Also launches an S3 bucket which is configured as a static webpage containing a picture of the WIT logo, gotten from a frequently changing URL. 

## Getting Started

### Dependencies

* Set up and tested on Ubuntu 20.04 

### Setup
* You must configure aws on your machine if you have not already (Below is for Linux installation).
```
$ sudo pip3 install awscli
$ aws configure
```
* Proceed to fill out prompts and continue to installation of project.


### Installing

* Create a folder in which you will house this prokect. Navigate to it via the command line.
* Linux Example:
 ``` 
 $ mkdir project-directory
 $ cd project-directory
 ```
 * Clone the repository
 ```
 $ git clone https://github.com/bryankeane0/boto3-ec2-s3-project.git
 ```
 

### Executing program

* Change python file permissions and run
```
$ chmod +x assignment1.py
$ python3 assignment1.py
```

## Help

Any advise for common problems or issues.
```
command to run if program contains helper info
```

## Authors

- Bryan Keane @ https://github.com/bryankeane0


## License

This project is licensed under the Unlicensed License - see the LICENSE.md file for details
