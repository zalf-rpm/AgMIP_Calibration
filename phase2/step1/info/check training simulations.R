# program to do first check of numerical results French data

rm(list=ls())

########## change character strings in 2 instructions below###########
# 1. change path to folder where your observed and simulated results are
setwd("C:\\Users\\Daniel Wallach\\Dropbox\\calibration\\ARVALIS data\\")
# 2. put name of the file with your numerical results
fileName<-"cal2_results numerical test.txt"
######################################################################

# read training data
dataARVALIS<-read.table("cal2_phenology mgt soil data.txt",header=TRUE,
	as.is=TRUE)
obs<-dataARVALIS[,c(3,100,101,103,104)]
colnames(obs)<-c("site","variety","sow","BBCH30","BBCH55")
# convert dates to date objects
obs$sow<-as.Date(obs$sow,format="%d/%m/%Y")
obs$BBCH30<-as.Date(obs$BBCH30,format="%d/%m/%Y")
obs$BBCH55<-as.Date(obs$BBCH55,format="%d/%m/%Y")
#print(obs)

# read simulation results
# from same folder as observed results
sim<-read.table(fileName,header=TRUE,
	colClasses="character")
# give columns simpler names
colnames(sim)<-c("number","site","variety","sow","emergence","BBCH30","BBCH55")
# convert dates to date objects
sim$emergence<-as.Date(sim$emergence,format="%d/%m/%Y")
sim$sow<-as.Date(sim$sow,format="%d/%m/%Y")
sim$BBCH30<-as.Date(sim$BBCH30,format="%d/%m/%Y")
sim$BBCH55<-as.Date(sim$BBCH55,format="%d/%m/%Y")
#sim

# merge the observed and simulated tables
obsSimAll<-merge(obs,sim,by=c("site","variety","sow"),
	suffixes=c(".obs",".sim"))
# remove rows with NA
obsSim<-obsSimAll[!is.na(obsSimAll$BBCH30.obs),]

# function to draw graphs of observed vs simulated and residuals vs simulated
plotFun<-function(obsSimBoth,stage,variety)
{
	obsSim<-obsSimBoth[obsSimBoth$variety==variety,]
	DASObs<-obsSim[,paste(stage,".obs",sep="")]-obsSim$sow
	DASSim<-obsSim[,paste(stage,".sim",sep="")]-obsSim$sow
	# print observed and simulated DAS for one variety
	print(cbind(obsSim[,1:3],DASObs,DASSim))
	# calculate RMSE and EF
	MSE<-mean((as.numeric(DASObs-DASSim))^2)
	RMSE<-sqrt(MSE)
	MSEMean<-mean((as.numeric(DASObs-mean(DASObs)))^2)
	EF<-1-MSE/MSEMean
	# plot observed -simulated
	plot(DASSim,DASObs,main=paste(variety,stage),
	  sub=paste("n=",length(DASSim),"RMSE=",round(RMSE,2),"EF=",round(EF,2)),
	  xlab="simulated days after sowing",
	  ylab="observed days after sowing")
	abline(0,1)
	# plot residuals
	plot (DASSim,DASObs-DASSim,main=paste(variety,stage),
	  xlab="simulated days after sowing",
	  ylab="residuals obs-sim days after sowing")
	abline(0,0)# end of function plotFun
	# after BBCH55, draw histogram of days from sowing to emergence
	if (stage=="BBCH55") hist(as.numeric(obsSim$emergence-obsSim$sow),
	  main=paste(variety,"emergence"),
	  xlab=paste("days from sowing to emergence" )) 
}  # end of plotFun

# call function to draw graphs for Apache
	dev.new()
	par(mfrow=c(3,2))
	plotFun(obsSim,"BBCH30","Apache")
	plotFun(obsSim,"BBCH55","Apache")
# call function to draw graphs for Bermude
	dev.new()
	par(mfrow=c(3,2))
	plotFun(obsSim,"BBCH30","Bermude")
	plotFun(obsSim,"BBCH55","Bermude")

