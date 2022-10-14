Do the disperseNN methods and architecture work in populations with long-range dispersal? Simulate populations where offspring dispersal distances are drawn from the following jump kernel:

$$ J(r) = \begin{cases}
A/\sigma & r\leq \sigma \\
(A/\sigma) (r/\sigma)^{-(\alpha+1)} & r > \sigma \end{cases}
$$

where $\sigma$ is the same distance that sets the length scales of dispersal, mate choice, and competition in the original disperseNN framework, $\alpha$ (the "kernel exponent") determines the weight of the long distance tail of the jump kernel, and $A = \frac{\alpha}{\alpha+1}$ is the normalization constant. 
