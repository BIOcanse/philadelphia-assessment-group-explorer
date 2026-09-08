# Independent base-R reproduction. Run from the research project root.
# No packages are required. This script does not change prior analysis files.
sales <- read.csv('data/processed/sales_clean.csv', colClasses=c(parcel_id='character'))
s <- sales[sales$sale_year == 2017, ]
stopifnot(nrow(s) == 8595, length(unique(s$parcel_id)) == 8595)
fit <- lm(log(assessed_value) ~ log(sale_price), data=s)
X <- model.matrix(fit)
e <- residuals(fit)
U <- rowsum(X * e, s$parcel_id)
n <- nrow(X); G <- nrow(U); k <- ncol(X)
B <- solve(crossprod(X))
V <- G/(G-1) * (n-1)/(n-k) * B %*% crossprod(U) %*% B
se <- sqrt(V[2,2]); beta <- coef(fit)[2]
t_stat <- (beta-1)/se
answer <- data.frame(n=n, beta=beta, se=se, t=t_stat, df=G-1,
                     p_value=2*pt(-abs(t_stat),G-1),
                     ci_low=beta-qt(.975,G-1)*se,
                     ci_high=beta+qt(.975,G-1)*se,
                     pearson=cor(s$sale_price,s$assessed_value),
                     ols_r2=summary(fit)$r.squared)
expected <- read.csv('outputs/research_story/proportionality.csv')
stopifnot(abs(answer$beta-expected$beta[1]) < 1e-10,
          abs(answer$se-expected$se[1]) < 1e-10)
print(answer)
p <- read.csv('outputs/conditional/main_predictions.csv')
for (kind in c('original','global','additive','interaction')) {
  f <- p[[paste0('spatial_',kind)]]
  r2 <- 1-sum((p$ratio-f)^2)/sum((p$ratio-mean(p$ratio))^2)
  cat(kind, ' direct spatial OOF q R-squared: ', r2, '\n')
}
# Write only the new report's verification artifact.
write.csv(answer,'outputs/research_story/r_verification.csv',row.names=FALSE)
